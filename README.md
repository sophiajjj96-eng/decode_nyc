# Algorithm Explained

Multimodal civic AI agent that helps NYC residents understand government algorithms through natural text and voice conversations.

## What It Does

Ask questions about NYC algorithmic tools and get factual answers based on official compliance data:

- **Text mode:** Type questions, get instant answers
- **Voice mode:** Speak naturally, hear responses

The agent queries the [NYC Algorithmic Tools Compliance Report](https://data.cityofnewyork.us/City-Government/Algorithmic-Tools-Compliance-Report/jaw4-yuem) to explain what algorithmic tools NYC agencies use, how they work, and how they might affect residents.

## Quick Start

```bash
cd algorithm-explained
uv sync
cp backend/env.example backend/.env
# Add your GOOGLE_API_KEY to backend/.env
export SSL_CERT_FILE=$(uv run --project backend python -m certifi)
uv run --project backend uvicorn backend.main:app --reload
```

Open `http://localhost:8000` and try asking:
- "What algorithmic tools does the NYPD use?"
- "Does NYC use facial recognition?"
- "How do housing algorithms work?"

## Documentation

- [QUICKSTART.md](docs/QUICKSTART.md) - Installation and basic usage
- [REFERENCE.md](docs/REFERENCE.md) - Technical architecture and API
- [DEVELOPMENT.md](docs/DEVELOPMENT.md) - Contributing and development
- [DEPLOYMENT.md](docs/DEPLOYMENT.md) - Deploy to Cloud Run

## Tech Stack

- **Frontend:** Vanilla JavaScript + Web Audio API
- **Backend:** FastAPI + Google ADK
- **AI:** Gemini 2.5 Flash with native audio
- **Data:** NYC Open Data API

## Features

- Real-time voice conversations with sub-500ms latency
- Official NYC dataset integration for factual answers
- WebSocket streaming for text and audio
- Session management with conversation history
- Beautiful, accessible UI design

## Requirements

- Python 3.13+
- Google API key (get at [AI Studio](https://aistudio.google.com/apikey))
- Modern browser (Chrome, Edge, Safari)
- Microphone for voice mode

## Resources

- [ADK Documentation](https://google.github.io/adk-docs/)
- [Gemini Live API](https://ai.google.dev/gemini-api/docs/live)
- [NYC Open Data](https://data.cityofnewyork.us/City-Government/Algorithmic-Tools-Compliance-Report/jaw4-yuem)
