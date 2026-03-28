"""Demo response interceptor for hard-coded demo conversations."""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DEMO_RESPONSES_PATH = Path(__file__).parent.parent / "data" / "demo_responses.json"

_demo_responses_cache = None


def load_demo_responses() -> list[dict]:
    """Load demo responses from JSON file (with caching)."""
    global _demo_responses_cache
    
    if _demo_responses_cache is not None:
        return _demo_responses_cache
    
    try:
        with DEMO_RESPONSES_PATH.open("r", encoding="utf-8") as f:
            _demo_responses_cache = json.load(f)
            logger.info(f"Loaded {len(_demo_responses_cache)} demo response patterns")
            return _demo_responses_cache
    except Exception as e:
        logger.error(f"Failed to load demo responses: {e}")
        return []


def normalize_text(text: str) -> str:
    """Normalize text for matching."""
    return text.lower().strip()


def count_keyword_matches(question: str, patterns: list[str]) -> int:
    """Count how many pattern keywords appear in the question."""
    normalized_question = normalize_text(question)
    matches = 0
    
    for pattern in patterns:
        normalized_pattern = normalize_text(pattern)
        if normalized_pattern in normalized_question:
            matches += 1
    
    return matches


def match_demo_question(user_question: str) -> dict | None:
    """Fuzzy match user question against demo questions.
    
    Uses keyword matching to detect demo questions even if phrasing varies.
    
    Args:
        user_question: The user's question text
        
    Returns:
        Matched demo response dict or None if no match
    """
    demo_responses = load_demo_responses()
    
    if not demo_responses:
        return None
    
    for demo in demo_responses:
        patterns = demo.get("question_patterns", [])
        required_keywords = demo.get("required_keywords", 2)
        
        matches = count_keyword_matches(user_question, patterns)
        
        if matches >= required_keywords:
            logger.info(
                f"Demo question matched: {demo['id']} "
                f"({matches}/{len(patterns)} patterns matched)"
            )
            return demo
    
    return None


def get_demo_response(user_question: str) -> dict | None:
    """Get hard-coded demo response if question matches.
    
    Args:
        user_question: The user's question text
        
    Returns:
        Dictionary with response, followup_questions, or None if no match
    """
    matched = match_demo_question(user_question)
    
    if matched:
        return {
            "response": matched.get("response", ""),
            "followup_questions": matched.get("followup_questions", []),
            "demo_id": matched.get("id", ""),
        }
    
    return None


def should_intercept(user_question: str) -> bool:
    """Check if this question should trigger demo interception.
    
    Args:
        user_question: The user's question text
        
    Returns:
        True if question matches a demo pattern
    """
    return match_demo_question(user_question) is not None
