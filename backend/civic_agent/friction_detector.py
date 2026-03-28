"""Friction detection - turns user skepticism into bias detection signals."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# Friction signal patterns (skepticism, confusion, concern)
FRICTION_PATTERNS = {
    "skeptical": [
        r"why is (my|mine|our) .*lower",
        r"why (am i|are we) not eligible",
        r"doesn't (make sense|seem fair|seem right)",
        r"that('s| is) not fair",
        r"how is that (fair|right|possible)",
        r"why (do|does) .* penalize",
        r"(doesn't|does not) sound (fair|right)",
        r"why (am i|are we) being punished",
        r"that seems (unfair|wrong|biased)",
        r"(is|are) (this|that|they) discriminat",
        r"why (am i|are we) scored lower",
    ],
    "confused": [
        r"(i|we) (don't|do not) understand (why|how)",
        r"what do you mean by",
        r"can you explain (that|this) again",
        r"(i'm|i am|we're|we are) confused",
        r"(that|this) (doesn't|does not) make sense",
        r"why would .* matter",
        r"what does .* have to do with",
        r"how can .* affect",
        r"(i|we) didn't know",
        r"nobody told (me|us)",
    ],
    "concerned": [
        r"(worried|concerned|afraid|scared) (about|that)",
        r"what if .* (happens|happened)",
        r"will (this|that) affect",
        r"can (this|that) hurt",
        r"is (this|that) going to",
        r"should (i|we) be (worried|concerned)",
        r"(is|are) (they|you) (tracking|watching|monitoring)",
        r"who (has access|can see)",
        r"what (about|if) my (privacy|rights)",
    ],
    "prior_contact_friction": [
        r"(because|since) (i|we) (needed|used|asked for|got) help before",
        r"(penalize|punish).*(for|because).*(help|service|assistance)",
        r"past (contact|history|record)",
        r"prior (dhs|acs|involvement|investigation)",
        r"(shouldn't|should not) (matter|count|affect)",
    ],
    "process_friction": [
        r"no (appeal|way to appeal|way to challenge)",
        r"can't (appeal|challenge|contest)",
        r"how (do i|can i|to) (appeal|challenge|contest)",
        r"what if (they're|it's|the score is) wrong",
        r"(nobody|no one) (explained|told me)",
        r"didn't (know|realize|understand)",
    ],
}


def calculate_friction_score(question: str) -> tuple[float, list[str]]:
    """Calculate friction score for a question.
    
    Args:
        question: User's question text
        
    Returns:
        (friction_score, matched_categories) where score is 0.0-1.0
    """
    lower_question = question.lower()
    matched_categories = []
    total_matches = 0
    
    for category, patterns in FRICTION_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, lower_question):
                matched_categories.append(category)
                total_matches += 1
                break  # Count category once even if multiple patterns match
    
    # Calculate friction score (0.0 = no friction, 1.0 = high friction)
    if total_matches == 0:
        return 0.0, []
    elif total_matches == 1:
        return 0.5, matched_categories
    else:
        # Multiple friction signals = higher score
        return min(0.3 + (total_matches * 0.25), 1.0), matched_categories


def detect_sentiment(question: str, friction_categories: list[str]) -> str:
    """Determine sentiment based on friction categories.
    
    Args:
        question: User's question text
        friction_categories: List of matched friction categories
        
    Returns:
        Sentiment label: skeptical, confused, concerned, or neutral
    """
    if not friction_categories:
        return "neutral"
    
    # Priority order: skeptical > concerned > confused
    if "skeptical" in friction_categories or "prior_contact_friction" in friction_categories:
        return "skeptical"
    elif "concerned" in friction_categories:
        return "concerned"
    elif "confused" in friction_categories:
        return "confused"
    else:
        return "questioning"


def detect_algorithm_context(question: str) -> str | None:
    """Detect which algorithm the friction relates to.
    
    Args:
        question: User's question text
        
    Returns:
        Algorithm ID or None
    """
    lower = question.lower()
    
    # Specific algorithm mentions
    if "homebase" in lower or "dhs" in lower:
        return "homebase_raq"
    elif "myschools" in lower or "school match" in lower or "school assignment" in lower:
        return "myschools"
    elif "acs" in lower and ("child" in lower or "family" in lower):
        return "acs_repeat_maltreatment"
    elif "shotspotter" in lower or "gunshot" in lower:
        return "shotspotter"
    
    # Topic-based detection
    if any(word in lower for word in ["housing", "homeless", "eviction", "shelter"]):
        return "homebase_raq"
    elif any(word in lower for word in ["school", "student", "education"]):
        return "myschools"
    elif any(word in lower for word in ["child services", "investigation", "family services"]):
        return "acs_repeat_maltreatment"
    elif any(word in lower for word in ["police", "patrol", "surveillance"]):
        return "shotspotter"
    
    return None


def log_friction_event(
    question: str,
    friction_score: float,
    sentiment: str,
    algorithm_id: str | None = None,
    categories: list[str] = None,
) -> None:
    """Log a friction event for bias detection analysis.
    
    Args:
        question: The user's question
        friction_score: Calculated friction score (0.0-1.0)
        sentiment: Detected sentiment
        algorithm_id: Related algorithm if detected
        categories: Matched friction categories
    """
    if friction_score < 0.3:
        # Don't log low-friction interactions
        return
    
    try:
        log_dir = Path(__file__).parent.parent / "data"
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / "friction_events.jsonl"
        
        event = {
            "question": question,
            "friction_score": round(friction_score, 2),
            "sentiment": sentiment,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        if algorithm_id:
            event["algorithm_id"] = algorithm_id
        
        if categories:
            event["categories"] = categories
        
        with log_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
        
    except Exception as e:
        print(f"Warning: Could not log friction event: {e}")


async def analyze_friction(question: str) -> dict[str, Any]:
    """Analyze a question for friction signals and log high-friction events.
    
    Args:
        question: User's question text
        
    Returns:
        Analysis dict with friction_score, sentiment, algorithm_id, categories
    """
    friction_score, categories = calculate_friction_score(question)
    sentiment = detect_sentiment(question, categories)
    algorithm_id = detect_algorithm_context(question)
    
    # Log high-friction events
    if friction_score >= 0.3:
        log_friction_event(
            question=question,
            friction_score=friction_score,
            sentiment=sentiment,
            algorithm_id=algorithm_id,
            categories=categories,
        )
    
    return {
        "friction_score": friction_score,
        "sentiment": sentiment,
        "algorithm_id": algorithm_id,
        "categories": categories,
        "is_high_friction": friction_score >= 0.5,
    }


def load_friction_events(limit: int = 100) -> list[dict[str, Any]]:
    """Load recent friction events from log file.
    
    Args:
        limit: Maximum number of events to load
        
    Returns:
        List of friction events (most recent first)
    """
    try:
        log_file = Path(__file__).parent.parent / "data" / "friction_events.jsonl"
        
        if not log_file.exists():
            return []
        
        events = []
        with log_file.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    events.append(json.loads(line))
        
        # Return most recent first
        events.reverse()
        return events[:limit]
        
    except Exception as e:
        print(f"Warning: Could not load friction events: {e}")
        return []


def aggregate_friction_stats() -> dict[str, Any]:
    """Aggregate friction statistics for reporting.
    
    Returns:
        Stats dict with algorithm breakdown, sentiment distribution, top questions
    """
    events = load_friction_events(limit=1000)
    
    if not events:
        return {
            "total_events": 0,
            "by_algorithm": {},
            "by_sentiment": {},
            "top_questions": [],
        }
    
    # Count by algorithm
    by_algorithm: dict[str, int] = {}
    by_sentiment: dict[str, int] = {}
    
    for event in events:
        algo_id = event.get("algorithm_id", "unknown")
        sentiment = event.get("sentiment", "neutral")
        
        by_algorithm[algo_id] = by_algorithm.get(algo_id, 0) + 1
        by_sentiment[sentiment] = by_sentiment.get(sentiment, 0) + 1
    
    # Find top questions (by friction score)
    sorted_events = sorted(events, key=lambda e: e.get("friction_score", 0), reverse=True)
    top_questions = [
        {
            "question": e["question"],
            "friction_score": e["friction_score"],
            "sentiment": e["sentiment"],
            "algorithm_id": e.get("algorithm_id"),
        }
        for e in sorted_events[:10]
    ]
    
    return {
        "total_events": len(events),
        "by_algorithm": by_algorithm,
        "by_sentiment": by_sentiment,
        "top_questions": top_questions,
    }
