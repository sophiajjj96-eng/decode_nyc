import json
import os

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("Missing GEMINI_API_KEY in .env")

client = genai.Client(api_key=api_key)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten later if you deploy
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MODEL = "gemini-2.5-flash"
DATASET_URL = "https://data.cityofnewyork.us/resource/jaw4-yuem.json"


class AskRequest(BaseModel):
    question: str


@app.get("/")
async def root():
    return {"status": "running"}


@app.get("/health")
async def health():
    return {"ok": True}


@app.get("/dataset/sample")
async def dataset_sample():
    rows = await fetch_dataset_rows(limit=5)
    return {
        "dataset": "Algorithmic Tools Compliance Report",
        "count": len(rows),
        "rows": rows,
    }


@app.post("/ask")
async def ask(req: AskRequest):
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        # 1) pull a chunk of live dataset rows
        rows = await fetch_dataset_rows(limit=200)

        # 2) keep only rows that seem relevant to the question
        matched_rows = filter_rows_for_question(rows, question, max_rows=8)

        # fallback if no obvious matches
        if not matched_rows:
            matched_rows = rows[:5]

        # 3) send question + dataset evidence to Gemini
        prompt = build_prompt(question, matched_rows)

        response = client.models.generate_content(
            model=MODEL,
            contents=prompt,
        )

        answer = response.text if hasattr(response, "text") else str(response)

        return {
            "question": question,
            "answer": answer,
            "rows_used": len(matched_rows),
            "rows": matched_rows,
        }

    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Dataset request failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def fetch_dataset_rows(limit: int = 50) -> list[dict]:
    params = {
        "$limit": min(max(limit, 1), 100)
    }

    async with httpx.AsyncClient(timeout=20.0) as http:
        resp = await http.get(DATASET_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

    return data if isinstance(data, list) else []


def filter_rows_for_question(rows: list[dict], question: str, max_rows: int = 8) -> list[dict]:
    """
    Very simple MVP retrieval:
    - split user question into keywords
    - score each row by keyword overlap against all text values in the row
    - return top matches
    """
    stopwords = {
        "the", "a", "an", "is", "are", "was", "were", "do", "does", "did",
        "to", "for", "of", "in", "on", "at", "and", "or", "with", "about",
        "what", "which", "who", "how", "why", "when", "where", "can", "could",
        "would", "should", "me", "my", "you", "your", "it", "this", "that"
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

        # small boosts for common likely intent words
        if "nypd" in keywords and "nypd" in haystack:
            score += 3
        if "police" in keywords and "police" in haystack:
            score += 2
        if "housing" in keywords and "housing" in haystack:
            score += 2
        if "education" in keywords and "education" in haystack:
            score += 2
        if "tool" in keywords and "tool" in haystack:
            score += 1
        if "algorithm" in keywords and "algorithm" in haystack:
            score += 1
        if "ai" in keywords and "ai" in haystack:
            score += 1

        if score > 0:
            scored.append((score, row))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [row for _, row in scored[:max_rows]]


def build_prompt(question: str, rows: list[dict]) -> str:
    return f"""
You are helping a user understand the NYC Open Data dataset
"Algorithmic Tools Compliance Report."

Rules:
- Answer using ONLY the dataset rows provided below.
- If the rows do not clearly answer the question, say that.
- Be concise and factual.
- Do not invent fields, agencies, tools, or conclusions.
- If useful, mention which agency or tool appears in the evidence.

User question:
{question}

Dataset rows:
{json.dumps(rows, indent=2)}

Now answer the user's question.
""".strip()