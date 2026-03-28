import json
import os
import re

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from google import genai

load_dotenv()

api_key = os.getenv("VERTEX_API_KEY")
if not api_key:
    raise RuntimeError("Missing VERTEX_API_KEY in .env")

client = genai.Client(vertexai=True, api_key=api_key)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MODEL = "gemini-2.5-flash"
DATASET_URL = "https://data.cityofnewyork.us/resource/jaw4-yuem.json"


class ChatMessage(BaseModel):
    role: str
    text: str


class AskRequest(BaseModel):
    question: str
    history: list[ChatMessage] = Field(default_factory=list)
    last_options: list[str] = Field(default_factory=list)
    current_topic: str | None = None
    current_subtopic: str | None = None
    clarification_depth: int = 0


@app.get("/")
async def root():
    return {"status": "running"}


@app.get("/health")
async def health():
    return {"ok": True}


@app.post("/ask")
async def ask(req: AskRequest):
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        resolved_question = resolve_short_reply(
            question=req.question,
            last_options=req.last_options,
            current_topic=req.current_topic,
            current_subtopic=req.current_subtopic,
        )

        rows = await fetch_dataset_rows(limit=100)
        matched_rows = filter_rows_for_question(rows, resolved_question, max_rows=12)

        if not matched_rows:
            matched_rows = rows[:5]

        intent = detect_intent(resolved_question)
        if intent == "unknown":
            try:
                intent = classify_intent_with_model(resolved_question, req.history)
            except Exception:
                intent = "factual"

        if intent == "broad" and should_offer_topic_menu(req, resolved_question):
            options = build_top_level_categories(matched_rows)
            return {
                "mode": "options",
                "answer": build_numbered_intro(
                    "NYC agencies use algorithmic tools in a few parts of daily life.",
                    options,
                    "Which one do you want to explore?",
                ),
                "options": options,
                "current_topic": None,
                "current_subtopic": None,
                "clarification_depth": 1,
            }

        if should_offer_subtopic_menu(req, resolved_question):
            options = build_subtopic_options(req.current_topic or resolved_question, matched_rows)
            if len(options) > 1:
                return {
                    "mode": "options",
                    "answer": build_numbered_intro(
                        f"Within {req.current_topic}, there are a few directions we can take.",
                        options,
                        "Which one do you want to explore?",
                    ),
                    "options": options,
                    "current_topic": req.current_topic,
                    "current_subtopic": None,
                    "clarification_depth": req.clarification_depth + 1,
                }


        prompt = build_prompt(
            question=resolved_question,
            history=req.history,
            rows=matched_rows[:4],
            current_topic=req.current_topic,
            current_subtopic=req.current_subtopic,
            clarification_depth=req.clarification_depth,
            intent = intent
        )

        response = client.models.generate_content(
            model=MODEL,
            contents=prompt,
        )

        answer = response.text if hasattr(response, "text") else str(response)
        answer = clean_answer(answer)

        next_topic = req.current_topic or infer_topic_from_question(resolved_question)
        next_subtopic = req.current_subtopic or infer_subtopic_from_question(resolved_question)

        return {
            "mode": "answer",
            "answer": answer,
            "options": [],
            "current_topic": next_topic,
            "current_subtopic": next_subtopic,
            "clarification_depth": req.clarification_depth,
        }

    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Dataset request failed: {str(e)}")
    except Exception as e:
        message = str(e)
        if "429" in message or "RESOURCE_EXHAUSTED" in message:
            raise HTTPException(
                status_code=429,
                detail="The AI service is temporarily out of quota. Please wait a minute and try again."
            )
        raise HTTPException(status_code=500, detail=message)


async def fetch_dataset_rows(limit: int = 50) -> list[dict]:
    params = {"$limit": min(max(limit, 1), 100)}

    async with httpx.AsyncClient(timeout=20.0) as http:
        resp = await http.get(DATASET_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

    return data if isinstance(data, list) else []


def filter_rows_for_question(rows: list[dict], question: str, max_rows: int = 8) -> list[dict]:
    stopwords = {
        "the", "a", "an", "is", "are", "was", "were", "do", "does", "did",
        "to", "for", "of", "in", "on", "at", "and", "or", "with", "about",
        "what", "which", "who", "how", "why", "when", "where", "can", "could",
        "would", "should", "me", "my", "you", "your", "it", "this", "that",
        "tell", "more", "know", "want", "like"
    }

    keywords = [
        word.strip(".,!?():;\"'").lower()
        for word in question.split()
    ]
    keywords = [word for word in keywords if len(word) > 1 and word not in stopwords]

    scored = []

    for row in rows:
        haystack = " ".join(str(v) for v in row.values()).lower()
        score = sum(1 for kw in keywords if kw in haystack)

        if "child" in keywords and "child" in haystack:
            score += 3
        if "children" in keywords and "children" in haystack:
            score += 3
        if "family" in keywords and "family" in haystack:
            score += 2
        if "housing" in keywords and "housing" in haystack:
            score += 2
        if "jail" in keywords and "jail" in haystack:
            score += 2
        if "health" in keywords and "health" in haystack:
            score += 2
        if "risk" in keywords and "risk" in haystack:
            score += 2
        if "algorithm" in keywords and "algorithm" in haystack:
            score += 1
        if "ai" in keywords and "ai" in haystack:
            score += 1

        if score > 0:
            scored.append((score, row))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [row for _, row in scored[:max_rows]]


def resolve_short_reply(
    question: str,
    last_options: list[str],
    current_topic: str | None,
    current_subtopic: str | None,
) -> str:
    text = question.strip().lower()

    option_map = {
        "1": 0,
        "one": 0,
        "first": 0,
        "the first one": 0,
        "2": 1,
        "two": 1,
        "second": 1,
        "the second one": 1,
        "3": 2,
        "three": 2,
        "third": 2,
        "the third one": 2,
        "4": 3,
        "four": 3,
        "fourth": 3,
        "the fourth one": 3,
        "5": 4,
        "five": 4,
        "fifth": 4,
        "the fifth one": 4,
    }

    if text in option_map and len(last_options) > option_map[text]:
        return f"Tell me more about {last_options[option_map[text]]}."

    if text == "both" and len(last_options) >= 2:
        return f"Tell me more about both {last_options[0]} and {last_options[1]}."

    if text in {"all", "all of them"} and last_options:
        joined = ", ".join(last_options[:3])
        return f"Give me a brief overview of {joined}."

    if current_subtopic and len(text.split()) <= 3:
        return f"Within {current_subtopic}, answer this follow-up: {question}"

    if current_topic and len(text.split()) <= 3:
        return f"Within {current_topic}, answer this follow-up: {question}"

    return question


def should_offer_subtopic_menu(req: AskRequest, resolved_question: str) -> bool:
    if not req.current_topic:
        return False
    if req.clarification_depth >= 2:
        return False

    broad_followups = {
        "tell me more",
        "more",
        "what about this",
        "explain more",
    }

    text = resolved_question.lower().strip()
    return text in broad_followups



def should_offer_topic_menu(req: AskRequest, resolved_question: str) -> bool:
    if req.current_topic or req.current_subtopic:
        return False
    return is_broad_question(resolved_question)


def is_broad_question(question: str) -> bool:
    text = question.lower().strip()

    broad_patterns = [
        r"tell me about ai use",
        r"tell me about ai",
        r"how is ai used",
        r"how does ai affect me",
        r"how does the government use ai",
        r"how does nyc use ai",
        r"what should i know about ai",
        r"what algorithms affect me",
    ]

    if any(re.search(pattern, text) for pattern in broad_patterns):
        return True

    if len(text.split()) <= 4 and any(word in text for word in ["ai", "algorithm", "algorithms"]):
        return True

    return False


def build_top_level_categories(rows: list[dict]) -> list[str]:
    labels = []
    haystack = " ".join(" ".join(str(v) for v in row.values()).lower() for row in rows)

    if any(word in haystack for word in ["child", "children", "family", "acs", "welfare"]):
        labels.append("Protecting children and supporting families")
    if any(word in haystack for word in ["jail", "correction", "detention", "custody"]):
        labels.append("Public safety and jails")
    if any(word in haystack for word in ["health", "illness", "foodborne", "disease"]):
        labels.append("Public health")
    if any(word in haystack for word in ["consumer", "inspection", "business", "worker protection"]):
        labels.append("Business inspections and consumer protection")
    if any(word in haystack for word in ["housing", "benefits", "services", "hra"]):
        labels.append("Housing and benefits")

    if not labels:
        labels = [
            "Children and families",
            "Public safety",
            "Public health",
        ]

    return labels[:5]


def build_subtopic_options(topic: str, rows: list[dict]) -> list[str]:
    topic_lower = topic.lower()
    haystack = " ".join(" ".join(str(v) for v in row.values()).lower() for row in rows)

    if any(word in topic_lower for word in ["children", "families", "child", "family"]):
        options = []
        if any(word in haystack for word in ["harm", "maltreatment", "risk", "asap"]):
            options.append("Predicting child safety risks")
        if any(word in haystack for word in ["staff", "caseload", "social worker", "workload"]):
            options.append("Planning social worker staffing")
        if any(word in haystack for word in ["outreach", "families with children", "service"]):
            options.append("Connecting families with services")
        return options[:4]

    return []


def build_numbered_intro(intro: str, options: list[str], question: str) -> str:
    lines = [intro, ""]
    for idx, option in enumerate(options, start=1):
        lines.append(f"{idx}. {option}")
    lines.append("")
    lines.append(question)
    return "\n".join(lines)


def infer_topic_from_question(question: str) -> str | None:
    text = question.lower()
    if any(word in text for word in ["child", "children", "family", "acs", "welfare"]):
        return "Protecting children and supporting families"
    if any(word in text for word in ["jail", "correction", "custody", "public safety"]):
        return "Public safety and jails"
    if any(word in text for word in ["health", "illness", "foodborne", "disease"]):
        return "Public health"
    return None


def infer_subtopic_from_question(question: str) -> str | None:
    text = question.lower()
    if any(word in text for word in ["harm", "maltreatment", "risk", "asap", "repeat maltreatment"]):
        return "Predicting child safety risks"
    return None


def clean_answer(answer: str) -> str:
    answer = answer.strip()

    paragraphs = [part.strip() for part in answer.split("\n\n") if part.strip()]
    if len(paragraphs) > 3:
        answer = "\n\n".join(paragraphs[:3])

    return answer

def detect_intent(question: str) -> str:
    text = question.lower().strip()

    impact_signals = [
        "does this affect me",
        "affect my life",
        "negative consequence",
        "negatively affect me",
        "should i worry",
        "is this fair",
        "could this hurt",
        "harm families",
        "what does this mean for me",
    ]
    if any(signal in text for signal in impact_signals):
        return "impact"

    follow_up_signals = [
        "tell me about something else",
        "what else",
        "go on",
        "tell me more",
        "why",
        "how so",
        "that's interesting",
        "thats interesting",
        "wait what",
    ]
    if any(signal in text for signal in follow_up_signals):
        return "follow_up"

    broad_signals = [
        "tell me about ai use",
        "tell me about ai",
        "how is ai used",
        "how does ai affect me",
        "how does the government use ai",
        "how does nyc use ai",
        "what should i know about ai",
        "what algorithms affect me",
    ]
    if any(signal in text for signal in broad_signals):
        return "broad"

    if len(text.split()) <= 4 and any(word in text for word in ["ai", "algorithm", "algorithms"]):
        return "broad"

    if any(word in text for word in ["what", "how", "which", "when", "where"]):
        return "factual"


    return "unknown"




def build_prompt(
    question: str,
    history: list[ChatMessage],
    rows: list[dict],
    current_topic: str | None,
    current_subtopic: str | None,
    clarification_depth: int,
    intent: str,
) -> str:
    history_text = "\n".join(
        f"{msg.role.upper()}: {msg.text}" for msg in history[-8:]
    ) or "No prior conversation."

    base = f"""
You are a conversational civic guide helping someone understand NYC's Algorithmic Tools Compliance Report.

Your job is to help a person understand how government algorithmic tools may affect them in everyday life.

General rules:
- Sound like a person, not a report.
- Use plain English and keep the reading level around 8th grade.
- Translate technical, legal, and agency language into everyday words.
- Use only the provided dataset evidence.
- If the evidence does not clearly support a claim, say so.
- Use the conversation history to avoid repeating information the user already heard.
- Do not restate the full background unless it is necessary for the new question.
- Stay focused on the current topic and subtopic unless the user asks to switch.

Current topic: {current_topic or "None"}
Current subtopic: {current_subtopic or "None"}
Clarification depth: {clarification_depth}

Conversation so far:
{history_text}

User question:
{question}

Relevant dataset evidence:
{json.dumps(rows, indent=2)}
""".strip()

    if intent == "impact":
        return base + """

Now answer in impact mode.

Rules for impact mode:
- Answer the user's concern directly in the first sentence.
- Focus on what the tool could mean for a person or family in practice.
- You may explain indirect effects, not just direct decisions.
- Do not simply repeat that the tool is "internal" unless that is essential.
- Briefly explain why the impact may be limited, indirect, or uncertain.
- Keep the answer to 2 short paragraphs max.
- End with one short follow-up question only if helpful.
""".strip()

    if intent == "follow_up":
        return base + """

Now answer in follow-up mode.

Rules for follow-up mode:
- Build directly on the previous turn.
- Do not restart from the beginning.
- Do not repeat facts already explained unless needed.
- Give a short, direct answer first.
- Then add one or two new details that move the conversation forward.
- Keep the answer brief and conversational.
- If the user asks for meaning, implications, or consequences, answer that directly instead of re-explaining the tool.

""".strip()

    return base + """

Now answer in factual mode.

Rules for factual mode:
- Start with exactly one short sentence that directly answers the question.
- Then add no more than 2 short paragraphs or one short list.
- Keep the answer brief, clear, and grounded in the evidence.
- Do not dump every matching row.
- End with one short follow-up question only when helpful.
""".strip()

def classify_intent_with_model(question: str, history: list[ChatMessage]) -> str:
    history_text = "\n".join(
        f"{msg.role.upper()}: {msg.text}" for msg in history[-4:]
    ) or "No prior conversation."

    prompt = f"""
Classify the user's latest message into exactly one of these labels:

- factual
- impact
- follow_up
- broad

Definitions:
- factual: asking for information about a tool, agency, service, or how something works
- impact: asking how something could affect a person, family, fairness, or possible harm
- follow_up: continuing the current thread conversationally without asking for a brand-new broad explanation
- broad: asking a general high-level question that could span multiple areas and should usually be narrowed first

Conversation so far:
{history_text}

Latest user message:
{question}

Respond with only one word:
factual
impact
follow_up
broad
""".strip()

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
    )

    text = response.text.strip().lower() if hasattr(response, "text") and response.text else "factual"

    if text in {"factual", "impact", "follow_up", "broad"}:
        return text

    return "factual"

