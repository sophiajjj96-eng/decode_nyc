# Algorithm, Explained

A multimodal civic AI agent helping NYC residents understand government algorithms through voice and text interaction.

## What It Does

Ask questions about NYC government algorithms in plain English. Get answers based on official NYC Open Data with bi-directional voice streaming powered by Google's ADK and Gemini Live API.

**Key Features**
- Natural voice conversations with real-time transcription
- Text-based Q&A interface
- Queries NYC Algorithmic Tools Compliance Report dataset
- Session-based context maintenance

## Quick Start

```bash
uv sync
cp backend/env.example backend/.env  # Add your GOOGLE_API_KEY
uv run --project backend uvicorn backend.main:app --reload
```

Open `http://localhost:8000` and start asking questions.

**Example questions:**
- "What algorithmic tools does the NYPD use?"
- "Does NYC use facial recognition?"
- "How do housing algorithms work?"

## Documentation

- [Setup Guide](docs/SETUP.md) - Installation and configuration
- [Usage Guide](docs/USAGE.md) - How to use the app
- [API Reference](docs/API.md) - WebSocket API details
- [Architecture](docs/ARCHITECTURE.md) - Technical design
- [Development](docs/DEVELOPMENT.md) - Contributing and testing

See [docs/](docs/) for complete documentation.

## Requirements

Python 3.13+, uv package manager, Google API key (Gemini Live API)

See [Setup Guide](docs/SETUP.md) for details.

## Resources

- [ADK Documentation](https://google.github.io/adk-docs/)
- [Gemini Live API](https://ai.google.dev/gemini-api/docs/live)
- [NYC Open Data](https://data.cityofnewyork.us/City-Government/Algorithmic-Tools-Compliance-Report/jaw4-yuem)
