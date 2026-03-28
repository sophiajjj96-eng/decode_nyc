# Documentation

Complete documentation for Algorithm Explained - a multimodal civic AI agent for understanding NYC government algorithms.

## Getting Started

- [Quick Start](QUICKSTART.md) - Get running in 60 seconds
- [Setup Guide](SETUP.md) - Detailed installation and configuration
- [Usage Guide](USAGE.md) - How to use text and voice modes

## Reference

- [API Reference](API.md) - WebSocket API specification
- [Architecture](ARCHITECTURE.md) - Technical design and system architecture
- [Dataset Tool](DATASET.md) - NYC data retrieval implementation

## Development

- [Development Guide](DEVELOPMENT.md) - Contributing, testing, code quality
- [UV Workspace](UV-WORKSPACE.md) - Workspace structure and commands
- [Integration History](INTEGRATION.md) - ADK integration details

## External Resources

- [ADK Documentation](https://google.github.io/adk-docs/) - Google Agent Development Kit
- [Gemini Live API](https://ai.google.dev/gemini-api/docs/live) - Real-time API documentation
- [NYC Open Data](https://data.cityofnewyork.us/City-Government/Algorithmic-Tools-Compliance-Report/jaw4-yuem) - Source dataset
- [Web Audio API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API) - Browser audio APIs

## Quick Links

**Installation:**
```bash
uv sync
cp backend/env.example backend/.env
uv run --project backend uvicorn backend.main:app --reload
```

**Key Concepts:**
- [NYC Dataset Tool](DATASET.md#tool-implementation) - How data retrieval works
- [WebSocket Events](API.md#event-types) - ADK event types
- [Audio Pipeline](ARCHITECTURE.md#audio-pipeline) - Voice processing flow

**Common Tasks:**
- [Adding a Tool](DEVELOPMENT.md#adding-a-new-tool)
- [Modifying Agent Instructions](DEVELOPMENT.md#modifying-agent-instructions)
- [Troubleshooting Setup](SETUP.md#troubleshooting)
