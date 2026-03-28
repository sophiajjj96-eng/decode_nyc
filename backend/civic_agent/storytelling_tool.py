"""Algorithm storytelling tool - transforms technical specs into human-centered narratives."""

import json
from pathlib import Path
from typing import Any

from google.adk.tools import FunctionTool


# Load algorithm data
ALGORITHMS_PATH = Path(__file__).parent.parent / "data" / "algorithms.json"
ALGORITHMS: list[dict[str, Any]] = []

try:
    with ALGORITHMS_PATH.open("r", encoding="utf-8") as f:
        ALGORITHMS = json.load(f)
except Exception as e:
    print(f"Warning: Could not load algorithms.json: {e}")


def get_algorithm_by_id(algo_id: str) -> dict[str, Any] | None:
    """Retrieve algorithm data by ID."""
    for algo in ALGORITHMS:
        if algo.get("id") == algo_id:
            return algo
    return None


def detect_algorithm_from_keywords(question: str) -> dict[str, Any] | None:
    """Detect which algorithm the user is asking about based on keywords."""
    lower_question = question.lower()
    
    for algo in ALGORITHMS:
        keywords = algo.get("trigger_keywords", [])
        if any(keyword in lower_question for keyword in keywords):
            return algo
    
    return None


async def explain_algorithm_story(
    algorithm_id: str,
    user_situation: str = "",
) -> str:
    """Explain an algorithm using plain-language storytelling instead of technical jargon.
    
    Args:
        algorithm_id: ID of the algorithm (homebase_raq, myschools, acs_repeat_maltreatment, shotspotter)
        user_situation: Optional description of the user's specific situation
        
    Returns:
        A human-centered narrative explanation of the algorithm with structured sections
    """
    algo = get_algorithm_by_id(algorithm_id)
    
    if not algo:
        return f"Algorithm '{algorithm_id}' not found in our database."
    
    name = algo.get("name", "Unknown Algorithm")
    agency = algo.get("agency", "Unknown Agency")
    plain_summary = algo.get("plain_summary", "")
    how_it_works = algo.get("how_it_works", "")
    inputs = algo.get("inputs", [])
    key_weights = algo.get("key_weights", {})
    fairness_concerns = algo.get("fairness_concerns", [])
    what_you_can_do = algo.get("what_you_can_do", [])
    storytelling_prompts = algo.get("storytelling_prompts", {})
    
    # Build structured narrative with visual sections
    story = f"# {name}\n\n"
    story += f"**{agency}**\n\n"
    story += f"{plain_summary}\n\n"
    
    # Section 1: What It Looks At (with visual indicators)
    if inputs:
        story += "## What DHS Considers\n\n"
        for input_factor in inputs:
            weight = key_weights.get(input_factor.replace(" ", "_"), "")
            
            # Visual risk score representation
            if weight == "high":
                indicator = "🔴 **High Impact**"
            elif weight == "medium":
                indicator = "🟡 **Medium Impact**"
            else:
                indicator = "⚪ **Considered**"
            
            story += f"- **{input_factor.title()}** {indicator}\n"
        story += "\n"
    
    # Section 2: How It Works (narrative + flowchart callout)
    story += "## How It Works\n\n"
    story += f"{how_it_works}\n\n"
    story += "_A decision tree flowchart will appear below showing the step-by-step process._\n\n"
    
    # Section 3: What This Means For You (personalized)
    if user_situation and storytelling_prompts:
        story += "## What This Means For You\n\n"
        user_lower = user_situation.lower()
        
        # Match situation to relevant prompts
        added_context = False
        if "prior" in user_lower or "before" in user_lower or "previous" in user_lower:
            if "prior_contact" in storytelling_prompts:
                story += "⚠️ " + storytelling_prompts["prior_contact"] + "\n\n"
                added_context = True
            elif "prior_contact_penalty" in storytelling_prompts:
                story += "⚠️ " + storytelling_prompts["prior_contact_penalty"] + "\n\n"
                added_context = True
        
        if "income" in user_lower or "money" in user_lower:
            if "income_factor" in storytelling_prompts:
                story += "💰 " + storytelling_prompts["income_factor"] + "\n\n"
                added_context = True
        
        if "family" in user_lower or "kids" in user_lower or "children" in user_lower:
            if "family_size_factor" in storytelling_prompts:
                story += "👨‍👩‍👧‍👦 " + storytelling_prompts["family_size_factor"] + "\n\n"
                added_context = True
        
        if not added_context:
            # Default personalized message
            story += "Based on your situation, this algorithm will evaluate multiple factors to determine your eligibility.\n\n"
    
    # Section 4: Known Fairness Issues (critical)
    if fairness_concerns:
        story += "## ⚠️ Known Fairness Issues\n\n"
        for concern in fairness_concerns:
            story += f"- {concern}\n"
        story += "\n"
    
    # Section 5: What You Can Do (actionable)
    if what_you_can_do:
        story += "## What You Can Do\n\n"
        for action in what_you_can_do:
            story += f"✓ {action}\n"
        story += "\n"
    
    return story


async def list_all_algorithms() -> str:
    """List all available algorithms with brief descriptions.
    
    Returns:
        Formatted list of algorithms
    """
    if not ALGORITHMS:
        return "No algorithm data available."
    
    result = "## NYC Government Algorithms We Track\n\n"
    
    for algo in ALGORITHMS:
        name = algo.get("name", "Unknown")
        agency = algo.get("agency", "Unknown")
        summary = algo.get("plain_summary", "")
        
        result += f"### {name}\n"
        result += f"**Agency**: {agency}\n\n"
        result += f"{summary}\n\n"
    
    return result


def get_algorithm_followup_questions(algorithm_id: str) -> list[str]:
    """Get contextual follow-up questions for a specific algorithm.
    
    Args:
        algorithm_id: Algorithm ID
        
    Returns:
        List of 3-4 follow-up questions
    """
    followup_map = {
        "homebase_raq": [
            "Is the algorithm fair to people who've needed help before?",
            "Is it a algorithm fair if I've used DHS services in the past?",
            "Can I appeal if my score is too low?",
            "What if my income situation has changed?",
        ],
        "myschools": [
            "Is the algorithm fair to students from low-income neighborhoods?",
            "Can I appeal my school assignment?",
            "How does the Probability of Acceptance score work?",
            "What if none of my ranked schools had space?",
        ],
        "acs_repeat_maltreatment": [
            "Do families know they're being scored?",
            "Is this fair to families who've been investigated before?",
            "Can I request a fair hearing?",
            "Who has access to my family's data?",
        ],
        "shotspotter": [
            "Why are sensors only in certain neighborhoods?",
            "What happens if it's a false alarm?",
            "Is this algorithm fair to my community?",
            "Can the city audit the vendor's training data?",
        ],
    }
    
    return followup_map.get(algorithm_id, [
        "Is this algorithm fair?",
        "What can I do if I disagree with the decision?",
        "Who can I contact for help?",
    ])


async def get_algorithm_with_followups(algorithm_id: str, user_situation: str = "") -> str:
    """Get algorithm explanation with suggested follow-up questions.
    
    Args:
        algorithm_id: Algorithm ID
        user_situation: Optional user context
        
    Returns:
        Formatted explanation with follow-up questions
    """
    # Get main explanation
    explanation = await explain_algorithm_story(algorithm_id, user_situation)
    
    # Add follow-up questions
    followups = get_algorithm_followup_questions(algorithm_id)
    
    if followups:
        explanation += "\n---\n\n**Follow-up questions:**\n\n"
        for idx, question in enumerate(followups, 1):
            explanation += f"{idx}. {question}\n"
    
    return explanation


# Create tools
algorithm_storyteller_tool = FunctionTool(explain_algorithm_story)
list_algorithms_tool = FunctionTool(list_all_algorithms)
algorithm_with_followups_tool = FunctionTool(get_algorithm_with_followups)
