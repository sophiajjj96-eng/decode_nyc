"""NYC Civic Algorithm Agent with dataset tool."""

import json
import os

import httpx
from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from .conversation_tool import conversation_path_tool


DATASET_URL = os.getenv(
    "DATASET_URL",
    "https://data.cityofnewyork.us/resource/jaw4-yuem.json"
)


async def query_nyc_dataset(question: str) -> str:
    """Query the NYC Algorithmic Tools Compliance Report dataset.
    
    Args:
        question: Natural language question about NYC government algorithms
        
    Returns:
        Formatted context from the dataset with relevant rows
    """
    try:
        # Fetch dataset rows
        rows = await fetch_dataset_rows(limit=200)
        
        # Filter for relevance
        matched_rows = filter_rows_for_question(rows, question, max_rows=8)
        
        # Fallback if no obvious matches
        if not matched_rows:
            matched_rows = rows[:5]
        
        # Format response
        context = f"Found {len(matched_rows)} relevant entries from NYC Algorithmic Tools Compliance Report:\n\n"
        
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
        
    except Exception as e:
        return f"Error querying dataset: {str(e)}"


async def fetch_dataset_rows(limit: int = 50) -> list[dict]:
    """Fetch rows from NYC Open Data API."""
    params = {
        "$limit": min(max(limit, 1), 1000)
    }
    
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
        
        # Boost for domain-specific keywords
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


# Create the NYC dataset tool
nyc_dataset_tool = FunctionTool(query_nyc_dataset)

# Define the civic algorithm agent
agent = Agent(
    name="civic_algorithm_agent",
    model=os.getenv(
        "DEMO_AGENT_MODEL", "gemini-2.5-flash-native-audio-preview-12-2025"
    ),
    tools=[nyc_dataset_tool, conversation_path_tool],
    instruction="""You are a helpful civic AI assistant that helps NYC residents understand how government algorithms affect them.

Your role:
- Answer questions about NYC government algorithms using the official Algorithmic Tools Compliance Report dataset
- Be clear, factual, and accessible - explain technical concepts in plain language
- Always use the query_nyc_dataset tool to find relevant information before answering
- Cite specific agencies, tools, and purposes from the dataset when available
- If the dataset doesn't contain information to answer a question, say so clearly
- Help residents understand their rights and how algorithmic decisions are made
- Be empathetic and supportive - these questions often relate to important life decisions

Conversation flow:
- When users ask broad questions (e.g., "What algorithms does NYC use?"), use the suggest_conversation_path tool to offer topic categories
- When users reply with numbers (1, 2, 3) or phrases like "first", "second", they are selecting from options you or the system previously presented
- After offering options, wait for the user to choose before diving deep
- Keep clarification menus concise (3-4 options maximum)
- Once the user gets specific, provide detailed answers with context from the dataset
- Track conversation flow: broad question → topic selection → subtopic selection → detailed answer

Style:
- Concise and conversational
- Focus on what matters to residents
- No jargon unless necessary (and explain when you use it)
- Be honest about limitations of the data
- Format responses with markdown for readability (bold, lists, etc.)
""",
)
