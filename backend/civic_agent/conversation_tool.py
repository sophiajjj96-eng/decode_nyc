"""Conversation flow management tools for multi-turn dialog."""

import json
import logging
import os
import re
from collections import Counter

from google import genai
from google.adk.tools import FunctionTool

from .state import ConversationState

logger = logging.getLogger(__name__)


def contains_any(text: str, phrases: list[str]) -> bool:
    """Return True if any phrase appears in the text."""
    return any(phrase in text for phrase in phrases)


def contains_topic_words(
    text: str,
    words: list[str],
    min_matches: int = 1,
) -> bool:
    """Return True if at least min_matches words appear in the text."""
    matches = sum(1 for word in words if word in text)
    return matches >= min_matches


def detect_intent(question: str) -> str:
    """Classify user intent.

    Returns one of:
    - broad
    - factual
    - impact
    - follow_up
    - unknown
    """
    text = question.lower().strip()

    impact_signals = [
        "does this affect me",
        "affect my life",
        "affect my family",
        "negative consequence",
        "negatively affect me",
        "harm me",
        "hurt me",
        "hurt families",
        "should i worry",
        "i'm worried",
        "im worried",
        "i am worried",
        "i'm concerned",
        "im concerned",
        "i am concerned",
        "is this fair",
        "could this hurt",
        "what does this mean for me",
        "what does this mean for my family",
        "is this bad",
        "is that a problem",
        "could this be harmful",
        "what are the consequences",
        "what are the risks",
        "why should i care",
        "classify me",
        "profile me",
        "label me",
    ]
    if contains_any(text, impact_signals):
        return "impact"

    if contains_topic_words(
        text,
        ["harm", "hurt", "risk", "consequence", "affect", "impact", "worry", "concern", "classify", "profile", "label"],
        min_matches=2,
    ):
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
        "can you explain that",
        "say more",
        "what do you mean",
        "okay but",
        "so then what",
        "and then what",
        "can you unpack that",
    ]
    if contains_any(text, follow_up_signals):
        return "follow_up"

    broad_signals = [
        "tell me about ai",
        "tell me about ai use",
        "tell me about algorithmic tools",
        "how is ai used",
        "how does ai affect me",
        "how does the government use ai",
        "how does nyc use ai",
        "what should i know about ai",
        "what algorithms affect me",
        "where does ai show up",
        "how is ai used in government",
        "how do city agencies use ai",
    ]
    if contains_any(text, broad_signals):
        return "broad"

    if len(text.split()) <= 4 and any(word in text for word in ["ai", "algorithm", "algorithms"]):
        return "broad"

    if any(word in text for word in ["what", "how", "which", "when", "where", "explain", "describe"]):
        return "factual"

    return "unknown"


def should_offer_topic_menu(state: ConversationState, question: str) -> bool:
    """Determine whether the user needs a top-level topic menu."""
    if state.current_topic or state.current_subtopic:
        return False

    intent = detect_intent(question)
    return intent == "broad"


def should_offer_subtopic_menu(
    state: ConversationState,
    question: str,
    available_rows: list[dict],
) -> bool:
    """Determine whether a subtopic menu is warranted."""
    if not state.current_topic:
        return False
    if state.current_subtopic:
        return False
    if state.clarification_depth >= 1:
        return False

    vague_followups = {
        "tell me more",
        "more",
        "go on",
        "what else",
    }

    text = question.lower().strip()
    if text not in vague_followups:
        return False

    options = build_subtopic_options(state.current_topic, available_rows)
    return len(options) >= 2


def resolve_short_reply(
    question: str,
    last_options: list[str],
    current_topic: str | None,
) -> str:
    """Resolve numbered or short replies to fuller prompts."""
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

    if text in {"all", "all of them", "everything"} and last_options:
        joined = ", ".join(last_options[:3])
        return f"Give me a brief overview of {joined}."

    if text in {"more", "tell me more", "go on", "continue", "yes"} and current_topic:
        return f"Tell me more about {current_topic}."

    return question


def build_top_level_categories(rows: list[dict]) -> list[str]:
    """Extract human-friendly top-level categories from dataset rows."""
    labels: list[str] = []
    haystack = " ".join(" ".join(str(v) for v in row.values()).lower() for row in rows)

    if any(word in haystack for word in ["child", "children", "family", "acs", "welfare"]):
        labels.append("Protecting children and supporting families")
    if any(word in haystack for word in ["jail", "correction", "detention", "custody", "police", "nypd"]):
        labels.append("Public safety and jails")
    if any(word in haystack for word in ["health", "illness", "foodborne", "disease", "mental health"]):
        labels.append("Public health")
    if any(word in haystack for word in ["consumer", "inspection", "business", "worker protection"]):
        labels.append("Business inspections and consumer protection")
    if any(word in haystack for word in ["housing", "benefits", "services", "hra", "homeless", "voucher"]):
        labels.append("Housing and benefits")

    if not labels:
        labels = [
            "Children and families",
            "Public safety",
            "Public health",
        ]

    return labels[:5]


def build_subtopic_options(topic: str, rows: list[dict]) -> list[str]:
    """Build subtopic options from current topic and dataset rows."""
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

    tool_names: list[str] = []
    for row in rows:
        tool_name = row.get("tool_name", "")
        if tool_name and tool_name not in tool_names and len(tool_names) < 4:
            tool_names.append(tool_name)

    return tool_names


def build_numbered_intro(intro_text: str, options: list[str], prompt: str) -> str:
    """Format a numbered menu response."""
    lines = [intro_text, ""]
    for idx, option in enumerate(options, 1):
        lines.append(f"{idx}. {option}")
    lines.append("")
    lines.append(prompt)
    return "\n".join(lines)


def infer_topic_from_question(question: str) -> str | None:
    """Infer broad topic from question text."""
    lower = question.lower()

    if any(word in lower for word in ["child", "children", "family", "acs", "welfare"]):
        return "Protecting children and supporting families"
    if any(word in lower for word in ["jail", "correction", "custody", "public safety", "police", "nypd"]):
        return "Public safety and jails"
    if any(word in lower for word in ["health", "illness", "foodborne", "disease"]):
        return "Public health"
    if any(word in lower for word in ["housing", "benefits", "voucher", "homeless", "shelter"]):
        return "Housing and benefits"

    return None


def infer_subtopic_from_question(question: str) -> str | None:
    """Infer narrower subtopic from question text."""
    lower = question.lower()

    if any(word in lower for word in ["harm", "maltreatment", "risk", "asap", "repeat maltreatment"]):
        return "Predicting child safety risks"

    return None


def clean_answer(answer: str) -> str:
    """Clean up model artifacts from answer text."""
    answer = answer.strip()

    patterns_to_remove = [
        r"\[NARRATION\]",
        r"\[/NARRATION\]",
        r"\[IMAGE_PROMPT\]",
        r"\[/IMAGE_PROMPT\]",
    ]
    for pattern in patterns_to_remove:
        answer = re.sub(pattern, "", answer, flags=re.IGNORECASE)

    paragraphs = [part.strip() for part in answer.split("\n\n") if part.strip()]
    if len(paragraphs) > 3:
        answer = "\n\n".join(paragraphs[:3])
    else:
        answer = "\n\n".join(paragraphs)

    return answer.strip()


async def classify_intent_with_model(question: str, history: list) -> str:
    """Fallback intent classifier for ambiguous cases."""
    api_key = os.getenv("VERTEX_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return detect_intent(question)

    history_text = "\n".join(
        f"{msg.role.upper()}: {msg.text}"
        for msg in history[-4:]
        if hasattr(msg, "role") and hasattr(msg, "text")
    ) or "No prior conversation."

    prompt = f"""
Classify the user's latest message into exactly one of these labels:

- factual
- impact
- follow_up
- broad

Definitions:
- factual: asking for information about a tool, agency, service, or how something works
- impact: asking how something could affect a person, family, fairness, classification, or possible harm
- follow_up: continuing the current thread conversationally without asking for a brand-new broad explanation
- broad: asking a general high-level question that should usually be narrowed first

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

    try:
        if os.getenv("VERTEX_API_KEY"):
            client = genai.Client(vertexai=True, api_key=os.getenv("VERTEX_API_KEY"))
        else:
            client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

        response = await client.aio.models.generate_content(
            model=os.getenv("TEXT_MODEL", "gemini-2.5-flash"),
            contents=prompt,
        )
        text = response.text.strip().lower() if response.text else "factual"

        if text in {"factual", "impact", "follow_up", "broad"}:
            return text
    except Exception as exc:
        logger.warning("Model intent classification failed: %s", exc)

    return detect_intent(question)


async def suggest_conversation_path(question: str, available_topics: list[str]) -> str:
    """Suggest topic paths for broad questions."""
    return build_numbered_intro(
        "NYC agencies use algorithmic tools in a few parts of daily life.",
        available_topics[:4] if len(available_topics) > 4 else available_topics,
        "Which one do you want to explore?",
    )


async def classify_intent_for_agent(question: str) -> str:
    """Expose intent classification to the agent."""
    return detect_intent(question)


def get_welcome_message() -> dict:
    """Get welcome message and starter prompts."""
    return {
        "message": "Ask me about NYC government algorithms and how they might affect you.",
        "prompts": [
            "How does the government use AI on me?",
            "What algorithmic tools does the NYPD use?",
            "How do housing algorithms affect me?",
            "Does NYC use AI in child services?",
        ],
    }


async def generate_followup_questions(conversation_history: list[dict[str, str]]) -> list[str]:
    """Generate suggested follow-up questions."""
    if not conversation_history:
        return []

    api_key = os.getenv("VERTEX_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return []

    try:
        if os.getenv("VERTEX_API_KEY"):
            client = genai.Client(vertexai=True, api_key=os.getenv("VERTEX_API_KEY"))
        else:
            client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

        formatted_history = "\n".join(
            f"{msg['role'].upper()}: {msg['text']}"
            for msg in conversation_history[-10:]
        )

        prompt = f"""
Based on this conversation about NYC government algorithms, suggest 3 concise next questions the user might ask.

Conversation history:
{formatted_history}

Requirements:
- Focus on NYC algorithmic tools and how they affect residents
- Keep each question under 14 words
- Return ONLY a JSON array of strings

Format:
["question 1", "question 2", "question 3"]
""".strip()

        response = await client.aio.models.generate_content(
            model=os.getenv("TEXT_MODEL", "gemini-2.5-flash"),
            contents=prompt,
        )

        response_text = response.text.strip() if response.text else "[]"

        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
            response_text = response_text.strip()

        questions = json.loads(response_text)

        if isinstance(questions, list) and all(isinstance(q, str) for q in questions):
            return questions[:4]
    except Exception as exc:
        logger.error("Error generating follow-up questions: %s", exc)

    return []


conversation_path_tool = FunctionTool(suggest_conversation_path)
intent_classifier_tool = FunctionTool(classify_intent_for_agent)
