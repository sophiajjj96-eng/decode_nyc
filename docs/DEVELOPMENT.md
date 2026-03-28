# Development Guide

## Project Structure

```
algorithm-explained/
├── pyproject.toml              # UV workspace definition
├── uv.lock                     # Shared dependency lockfile
├── .venv/                      # Virtual environment (auto-created)
├── backend/                    # Python subproject
│   ├── pyproject.toml         # Backend dependencies
│   ├── main.py                # FastAPI app + WebSocket
│   ├── civic_agent/
│   │   ├── __init__.py
│   │   └── agent.py           # ADK agent + NYC dataset tool
│   └── .env                   # Config (not committed)
├── frontend/                   # Static files
│   ├── index.html
│   ├── style.css
│   ├── app.js                 # WebSocket client
│   ├── audio-player.js
│   ├── audio-recorder.js
│   ├── pcm-player-processor.js
│   └── pcm-recorder-processor.js
└── docs/                       # Documentation
```

## UV Workspace

This project uses uv workspace pattern:
- **Workspace root**: Defines members, no dependencies
- **Backend subproject**: Independent Python package
- **Shared lockfile**: `uv.lock` ensures consistent versions

See [UV Workspace Guide](UV-WORKSPACE.md) for details.

## Development Setup

### Install Dependencies

```bash
cd algorithm-explained
uv sync
```

This creates `.venv/` and installs all workspace members.

### Configure Environment

```bash
cp backend/env.example backend/.env
```

Add your `GOOGLE_API_KEY` to `backend/.env`.

### Run Backend in Dev Mode

```bash
uv run --project backend uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

The `--reload` flag enables auto-reload on file changes.

## Making Changes

### Backend Changes

Edit files in `backend/`:
- `main.py` - WebSocket endpoint, FastAPI app
- `civic_agent/agent.py` - Agent definition and tools

Changes auto-reload when using `--reload` flag.

### Frontend Changes

Edit files in `frontend/`:
- `app.js` - WebSocket client logic
- `style.css` - UI styling
- Audio worklets (requires page refresh)

Refresh browser to see changes.

### Adding Dependencies

```bash
# Add to backend
uv add --project backend package-name

# Add dev dependency
uv add --project backend --dev package-name

# Remove dependency
uv remove --project backend package-name
```

## Code Quality

### Linting

```bash
# Check for issues
uv run --project backend ruff check .

# Auto-fix issues
uv run --project backend ruff check --fix .
```

### Formatting

```bash
# Format code
uv run --project backend ruff format .
```

### Type Checking

```bash
# Install mypy as dev dependency
uv add --project backend --dev mypy

# Run type checker
uv run --project backend mypy backend/
```

## Testing

### Running Tests

```bash
# Run all tests
uv run --project backend pytest

# Run specific test file
uv run --project backend pytest tests/test_agent.py

# Run with coverage
uv run --project backend pytest --cov=backend
```

### Writing Tests

Create tests in `backend/tests/`:

```python
import pytest
from civic_agent.agent import agent, query_nyc_dataset

@pytest.mark.asyncio
async def test_dataset_query():
    result = await query_nyc_dataset("What tools does NYPD use?")
    assert "NYPD" in result
    assert len(result) > 0
```

## Adding Features

### Adding a New Tool

1. Define tool function in `backend/civic_agent/agent.py`:

```python
async def new_tool_function(param: str) -> str:
    """Tool description that becomes tool schema.
    
    Args:
        param: Parameter description
        
    Returns:
        Result description
    """
    # Implementation
    return "result"

new_tool = FunctionTool(new_tool_function)
```

2. Add to agent's tools:

```python
agent = Agent(
    name="civic_algorithm_agent",
    model=os.getenv("DEMO_AGENT_MODEL", "..."),
    tools=[nyc_dataset_tool, new_tool],  # Add here
    instruction="..."
)
```

### Adding Frontend Features

1. Edit `frontend/app.js` for new UI interactions
2. Update `frontend/style.css` for styling
3. Maintain existing design language (Instrument Serif + DM Sans)

### Modifying Agent Instructions

Edit the `instruction` field in `backend/civic_agent/agent.py`:

```python
agent = Agent(
    name="civic_algorithm_agent",
    model=os.getenv("DEMO_AGENT_MODEL", "..."),
    tools=[nyc_dataset_tool],
    instruction="""Your updated instructions here..."""
)
```

## Debugging

### Backend Debugging

Enable debug logging in `backend/main.py`:

```python
logging.basicConfig(
    level=logging.DEBUG,  # Already set
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
```

View logs in terminal running uvicorn.

### Frontend Debugging

Open browser DevTools (F12):
- **Console**: JavaScript logs and errors
- **Network**: WebSocket frames and messages
- **Application**: Storage, permissions, media devices

### Testing Audio Pipeline

```javascript
// In browser console
navigator.mediaDevices.getUserMedia({ audio: true })
  .then(stream => console.log('Microphone OK'))
  .catch(err => console.error('Microphone error:', err));
```

### Testing WebSocket

```bash
# Install wscat
npm install -g wscat

# Connect and test
wscat -c "ws://localhost:8000/ws/test-user/test-session"

# Send message
> {"type": "text", "text": "hello"}
```

## Performance Optimization

### Dataset Caching

Add Redis cache for repeated queries:

```python
import redis

cache = redis.Redis(host='localhost', port=6379)

async def query_nyc_dataset(question: str) -> str:
    cache_key = f"dataset:{question}"
    cached = cache.get(cache_key)
    if cached:
        return cached.decode()
    
    result = await fetch_and_process_dataset(question)
    cache.setex(cache_key, 3600, result)  # 1 hour TTL
    return result
```

### Connection Pooling

Already implemented via `httpx.AsyncClient` in `agent.py`.

### Audio Buffer Tuning

Adjust ring buffer size in `frontend/pcm-player-processor.js`:

```javascript
this.bufferSize = 24000 * 180;  // 180 seconds default
```

## Deployment

### Environment Variables

Production `.env`:

```bash
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=your-prod-project
GOOGLE_CLOUD_LOCATION=us-central1
DEMO_AGENT_MODEL=gemini-live-2.5-flash-native-audio
DATASET_URL=https://data.cityofnewyork.us/resource/jaw4-yuem.json
```

### Running in Production

```bash
# Use production ASGI server
uv run --project backend gunicorn backend.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

### Docker (Future)

Create `Dockerfile`:

```dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY . .
RUN pip install uv && uv sync --project backend
CMD ["uv", "run", "--project", "backend", "uvicorn", "backend.main:app", "--host", "0.0.0.0"]
```

## Contributing

### Pull Request Process

1. Fork the repository
2. Create feature branch: `git checkout -b feature/your-feature`
3. Make changes with tests
4. Run code quality checks: `uv run --project backend ruff check .`
5. Format code: `uv run --project backend ruff format .`
6. Run tests: `uv run --project backend pytest`
7. Commit with clear message
8. Push and create pull request

### Code Style

- Follow PEP 8
- Use type hints
- Document public functions
- Keep functions focused and small
- Avoid unnecessary complexity

### Commit Messages

Use conventional commits:

```
feat: add caching for dataset queries
fix: resolve WebSocket reconnection issue
docs: update API reference
```

## Common Tasks

### View Dependency Tree

```bash
uv tree --project backend
```

### Update Dependencies

```bash
# Update all
uv lock --upgrade

# Update specific package
uv add --project backend "google-adk>=1.30.0"

# Sync after updates
uv sync
```

### Check for Security Issues

```bash
# Install safety
uv add --project backend --dev safety

# Scan dependencies
uv run --project backend safety check
```

## Architecture Decisions

### Why UV Workspace?

- Clean separation of backend subproject
- Shared lockfile for consistency
- Easy to add more subprojects later
- Standard Python project structure

### Why ADK Instead of Direct Gemini API?

- Session management built-in
- LiveRequestQueue for bi-directional streaming
- Tool calling abstraction
- Production-ready patterns

### Why Keyword-Based Retrieval?

- Fast (<100ms for 200 rows)
- No ML dependencies
- Simple to understand and debug
- Good enough for MVP

Future: Vector embeddings for semantic search.

### Why WebSocket Instead of SSE?

- Bi-directional streaming required
- Binary audio frames more efficient
- Lower latency for voice
- Industry standard for real-time

## Resources

- [UV Documentation](https://docs.astral.sh/uv/)
- [ADK Documentation](https://google.github.io/adk-docs/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Web Audio API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API)
