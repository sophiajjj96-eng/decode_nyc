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
    lower = question.lower().strip()

    if contains_any(
        lower,
        [
            "affect me",
            "impact me",
            "harm",
            "concern",
            "risk",
            "fair",
            "unfair",
            "biased",
            "accurate",
            "wrong",
        ],
    ):
        return "impact"

    if contains_any(lower, ["tell me more", "what else", "what about", "continue", "go on", "expand"]):
        return "follow_up"

    broad_patterns = [
        r"^(what|which|tell me about).*(algorithm|tool|system)s?\s*(are|do|does)",
        r"^how (many|much|does).*(nyc|city|government)",
        r"^(show|list|give).*(all|overview|summary)",
        r"^what (can|should|do) (i|you|we) (know|do)",
    ]

    for pattern in broad_patterns:
        if re.search(pattern, lower):
            return "broad"

    if contains_topic_words(lower, ["what", "how", "why", "when", "where", "who", "does", "is", "can"], min_matches=1):
        return "factual"

    return "unknown"


def should_offer_topic_menu(state: ConversationState, question: str) -> bool:
    """Determine if we should offer a top-level topic menu."""
    intent = detect_intent(question)
    
    if intent != "broad":
        return False
    
    if state.clarification_depth >= 2:
        return False
    
    if state.current_topic:
        return False
    
    return True


def should_offer_subtopic_menu(state: ConversationState, question: str) -> bool:
    """Determine if we should offer a subtopic menu."""
    if state.clarification_depth >= 3:
        return False
    
    if state.current_subtopic:
        return False
    
    if not state.current_topic and detect_intent(question) == "broad":
        return False
    
    return state.current_topic is not None


def resolve_short_reply(
    question: str,
    last_options: list[str],
    current_topic: str | None,
) -> str:
    """Resolve numbered or short replies to full questions."""
    text = question.strip().lower()
    
    option_map = {
        "1": 0, "one": 0, "first": 0, "the first one": 0,
        "2": 1, "two": 1, "second": 1, "the second one": 1,
        "3": 2, "three": 2, "third": 2, "the third one": 2,
        "4": 3, "four": 3, "fourth": 3, "the fourth one": 3,
        "5": 4, "five": 4, "fifth": 4, "the fifth one": 4,
    }
    
    if text in option_map and len(last_options) > option_map[text]:
        return f"Tell me more about {last_options[option_map[text]]}."
    
    if text == "both" and len(last_options) >= 2:
        return f"Tell me more about {last_options[0]} and {last_options[1]}."
    
    if text in ["all", "all of them", "everything"] and len(last_options) > 2:
        topics = ", ".join(last_options[:-1]) + f", and {last_options[-1]}"
        return f"Tell me more about {topics}."
    
    if text in ["more", "tell me more", "go on", "continue", "yes"]:
        if current_topic:
            return f"Tell me more about {current_topic}."
        elif last_options:
            return f"Tell me more about {last_options[0]}."
    
    return question


def build_top_level_categories(rows: list[dict]) -> list[str]:
    """Extract top-level categories from dataset rows."""
    agencies: Counter[str] = Counter()
    
    for row in rows:
        agency = row.get("agency_name", "")
        if agency:
            agencies[agency] += 1
    
    top_agencies = [agency for agency, _ in agencies.most_common(5)]
    
    if not top_agencies:
        return ["Housing and homelessness", "Education and schools", "Public safety", "Social services"]
    
    categories = []
    for agency in top_agencies[:4]:
        if "police" in agency.lower() or "nypd" in agency.lower():
            categories.append("Public safety and policing")
        elif "housing" in agency.lower() or "homeless" in agency.lower():
            categories.append("Housing and homelessness")
        elif "education" in agency.lower() or "school" in agency.lower():
            categories.append("Education and schools")
        elif "child" in agency.lower() or "acs" in agency.lower():
            categories.append("Child welfare and family services")
        else:
            short_name = agency.split(",")[0].strip()
            categories.append(short_name)
    
    return list(dict.fromkeys(categories))[:4]


def build_subtopic_options(topic: str, rows: list[dict]) -> list[str]:
    """Build subtopic options based on current topic and available data."""
    tool_names: list[str] = []
    
    for row in rows:
        tool_name = row.get("tool_name", "")
        if tool_name and len(tool_names) < 4:
            if tool_name not in tool_names:
                tool_names.append(tool_name)
    
    if not tool_names:
        return []
    
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
    """Extract topic from question text."""
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


async def suggest_conversation_path(
    question: str,
    available_topics: list[str],
) -> str:
    """Suggest a conversational path when the user asks broad questions.
    
    Args:
        question: The user's question
        available_topics: List of available topic areas from the dataset
        
    Returns:
        A formatted menu of options with guidance
    """
    return build_numbered_intro(
        "NYC agencies use algorithmic tools in several areas.",
        available_topics[:4] if len(available_topics) > 4 else available_topics,
        "Which area would you like to explore?",
    )


async def classify_intent_for_agent(question: str) -> str:
    """Classify the user's question intent to guide conversation flow.
    
    Args:
        question: The user's question
        
    Returns:
        Intent type: 'broad', 'factual', or 'followup'
    """
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
