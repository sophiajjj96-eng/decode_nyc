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


def detect_intent(question: str) -> str:
    """Classify user intent based on keywords and patterns.
    
    Returns: 'broad', 'factual', or 'followup'
    """
    lower = question.lower().strip()
    
    broad_patterns = [
        r"^(what|which|tell me about).*(algorithm|tool|system)s?\s*(are|do|does)",
        r"^how (many|much|does).*(nyc|city|government)",
        r"^(show|list|give).*(all|overview|summary)",
        r"^what (can|should|do) (i|you|we) (know|do)",
    ]
    
    for pattern in broad_patterns:
        if re.search(pattern, lower):
            return "broad"
    
    if any(word in lower for word in ["explain", "tell me more", "what about", "how about", "also"]):
        return "followup"
    
    return "factual"


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
    
    if any(word in lower for word in ["housing", "homeless", "eviction", "apartment", "shelter"]):
        return "Housing and homelessness"
    elif any(word in lower for word in ["school", "education", "student", "teacher"]):
        return "Education and schools"
    elif any(word in lower for word in ["police", "nypd", "patrol", "arrest", "crime"]):
        return "Public safety and policing"
    elif any(word in lower for word in ["child", "acs", "family", "welfare"]):
        return "Child welfare and family services"
    
    return None


def infer_subtopic_from_question(question: str) -> str | None:
    """Extract subtopic from question text."""
    lower = question.lower()
    
    if "shotspotter" in lower or "gunshot" in lower:
        return "ShotSpotter"
    elif "homebase" in lower or "raq" in lower:
        return "Homebase Risk Assessment"
    elif "myschools" in lower or "school match" in lower:
        return "MySchools matching"
    elif "acs" in lower and "predict" in lower:
        return "ACS Repeat Maltreatment Model"
    
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
    
    return answer.strip()


async def classify_intent_with_model(question: str, history: list) -> str:
    """Use the model to classify intent when keyword detection is insufficient.
    
    This is a fallback for edge cases. Returns 'broad', 'factual', or 'followup'.
    """
    if len(history) == 0:
        return "factual"
    
    recent_user_messages = [msg.text for msg in history[-3:] if msg.role == "user"]
    
    if len(recent_user_messages) > 1:
        return "followup"
    
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
    """Get welcome message and common prompts for new conversations.
    
    Returns:
        Dictionary with 'message' and 'prompts' keys
    """
    return {
        "message": "Ask me about NYC government algorithms and how they might affect you.",
        "prompts": [
            "What algorithmic tools does the NYPD use?",
            "How do housing algorithms affect me?",
            "Does NYC use AI for school admissions?",
            "Tell me about ShotSpotter",
        ]
    }


async def generate_followup_questions(conversation_history: list[dict[str, str]]) -> list[str]:
    """Generate logical next questions using Gemini based on conversation context.
    
    Args:
        conversation_history: List of conversation messages with role and text
        
    Returns:
        List of 3-4 suggested follow-up questions
    """
    if not conversation_history:
        return []
    
    try:
        client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
        
        # Use last 5 exchanges for context
        recent_history = conversation_history[-10:]
        
        # Format conversation history for prompt
        formatted_history = "\n".join([
            f"{msg['role'].upper()}: {msg['text']}"
            for msg in recent_history
        ])
        
        prompt = f"""Based on this conversation about NYC government algorithms, suggest 3-4 logical next questions the user might ask.

Conversation history:
{formatted_history}

Requirements:
- Make questions specific and actionable
- Focus on NYC algorithms and how they affect residents
- Keep questions concise (under 15 words each)
- Return ONLY a JSON array of question strings, no other text

Format: ["question1", "question2", "question3"]"""
        
        response = await client.aio.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=prompt,
        )
        
        response_text = response.text.strip()
        
        # Remove markdown code blocks if present
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
            response_text = response_text.strip()
        
        questions = json.loads(response_text)
        
        if isinstance(questions, list) and all(isinstance(q, str) for q in questions):
            return questions[:4]  # Max 4 questions
        
        logger.warning(f"Unexpected follow-up format: {questions}")
        return []
        
    except Exception as e:
        logger.error(f"Error generating follow-up questions: {e}")
        return []


conversation_path_tool = FunctionTool(suggest_conversation_path)
intent_classifier_tool = FunctionTool(classify_intent_for_agent)
