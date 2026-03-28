"""NYC Civic Algorithm Agent with dataset tool."""

import os

import httpx
from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from .conversation_tool import conversation_path_tool


DATASET_URL = os.getenv(
    "DATASET_URL",
    "https://data.cityofnewyork.us/resource/jaw4-yuem.json",
)


async def query_nyc_dataset(question: str) -> str:
    """Query the NYC Algorithmic Tools Compliance Report dataset."""
    try:
        rows = await fetch_dataset_rows(limit=200)
        matched_rows = filter_rows_for_question(rows, question, max_rows=8)

        if not matched_rows:
            matched_rows = rows[:5]

        context = (
            f"Found {len(matched_rows)} relevant entries from the NYC "
            f"Algorithmic Tools Compliance Report:\n\n"
        )

        for idx, row in enumerate(matched_rows, 1):
            agency = row.get("agency_name", "Unknown")
            tool_name = row.get("tool_name", "Unknown")
            description = row.get("tool_description", "No description")
            purpose = row.get("tool_purpose", "")

            context += f"{idx}. {agency} - {tool_name}\n"
            context += f"   Description: {description}\n"
            if purpose:
                context += f"   Purpose: {purpose}\n"
            context += "\n"

        return context

    except Exception as exc:
        return f"Error querying dataset: {str(exc)}"


async def fetch_dataset_rows(limit: int = 50) -> list[dict]:
    """Fetch rows from NYC Open Data API."""
    params = {"$limit": min(max(limit, 1), 1000)}

    async with httpx.AsyncClient(timeout=20.0) as http:
        resp = await http.get(DATASET_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

    return data if isinstance(data, list) else []


def filter_rows_for_question(rows: list[dict], question: str, max_rows: int = 8) -> list[dict]:
    """Simple keyword-based retrieval for dataset rows."""
    stopwords = {
        "the", "a", "an", "is", "are", "was", "were", "do", "does", "did",
        "to", "for", "of", "in", "on", "at", "and", "or", "with", "about",
        "what", "which", "who", "how", "why", "when", "where", "can", "could",
        "would", "should", "me", "my", "you", "your", "it", "this", "that",
        "tell", "more", "know", "want", "like",
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


nyc_dataset_tool = FunctionTool(query_nyc_dataset)

agent = Agent(
    name="civic_algorithm_agent",
    model=os.getenv(
        "DEMO_AGENT_MODEL",
        "gemini-2.5-flash-native-audio-preview-12-2025",
    ),
    tools=[nyc_dataset_tool, conversation_path_tool],
    instruction="""
You are a conversational civic guide helping NYC residents understand how government algorithmic tools may affect them in everyday life.

Your role:
- Answer questions about NYC government algorithms using the official Algorithmic Tools Compliance Report dataset.
- Always use the query_nyc_dataset tool before answering factual questions.
- Use only the dataset evidence you are given. If the evidence does not clearly support a claim, say so plainly.
- Explain technical, legal, and agency language in plain English.
- Focus on what matters to residents, not internal government jargon.
- Be honest about limitations and uncertainty.

Conversation behavior:
- Sound like a person, not a report.
- Avoid repeating the full background if the user already heard it.
- Build directly on the previous turn instead of restarting from scratch.
- Keep answers concise and easy to scan.
- Use at most 2 examples unless the user asks for more.
- End most answers with one short, natural follow-up question that helps continue the conversation.

Broad questions:
- If the user asks a broad, high-level question, use the suggest_conversation_path tool to offer 3 to 4 topic areas.
- Keep category options short and human-friendly.
- Once the user chooses a topic, stop giving broad menus and answer that topic directly.

Short replies and selections:
- If the user says "1", "2", "first", "second", or "both", interpret that as a selection from the most recent options already shown.
- Treat short replies in context rather than as brand-new questions.

Impact and concern questions:
- If the user asks how a tool could affect them, their family, or whether something is fair, harmful, risky, or concerning, answer that concern directly first.
- If the user expresses worry, fear, or concern, acknowledge that emotion in the first sentence.
- Do not jump straight into examples before addressing the user's concern.
- You may explain indirect effects, not just direct decisions.
- Do not rely only on phrases like "this is internal" if the real-world effect could still matter.

Follow-up questions:
- If the user says something like "what else", "tell me more", or "what do you mean", continue the thread naturally.
- Do not force a new menu unless the user is still truly vague.
- If the user asks for implications or consequences, answer that directly instead of repeating the same factual setup.

Style:
- Be conversational, calm, and supportive.
- Prefer short paragraphs or short lists.
- Avoid sounding like a compliance report.
- Use markdown for readability when helpful.
""",
)
