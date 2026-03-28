# Development Guide

Guide for developers contributing to Algorithm Explained.

## Project Structure

```
algorithm-explained/
├── pyproject.toml              # UV workspace definition
├── uv.lock                     # Shared lockfile
├── backend/                    # Python subproject
│   ├── pyproject.toml         # Backend dependencies
│   ├── main.py                # FastAPI + WebSocket
│   ├── civic_agent/
│   │   └── agent.py           # ADK agent + NYC tool
│   └── .env                   # Config (not committed)
└── frontend/                   # Static files
    ├── index.html
    ├── style.css
    ├── app.js                 # WebSocket client
    └── audio-*.js             # Audio worklets
```

**UV workspace pattern:**
- Workspace root defines members
- Backend is independent Python package
- Shared lockfile ensures consistent versions

## Setup

```bash
cd algorithm-explained
uv sync                        # Install all dependencies
cp backend/env.example backend/.env
# Add GOOGLE_API_KEY to backend/.env
```

## Running

```bash
# Dev mode with auto-reload
uv run --project backend uvicorn backend.main:app --reload

# Production mode
uv run --project backend gunicorn backend.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

## Making Changes

### Backend

Edit `backend/main.py` or `backend/civic_agent/agent.py`. Changes auto-reload with `--reload` flag.

### Frontend

Edit files in `frontend/`. Refresh browser to see changes.

### Dependencies

```bash
# Add package
uv add --project backend package-name

# Add dev dependency
uv add --project backend --dev package-name

# Remove package
uv remove --project backend package-name

# Update all
uv lock --upgrade && uv sync
```

## Adding Features

### New Tool

1. Define tool function in `backend/civic_agent/agent.py`:

```python
async def new_tool(param: str) -> str:
    """Tool description for schema generation.
    
    Args:
        param: Parameter description
        
    Returns:
        Result description
    """
    return "result"

tool = FunctionTool(new_tool)
```

2. Add to agent's tools list:

```python
agent = Agent(
    name="civic_algorithm_agent",
    model=os.getenv("DEMO_AGENT_MODEL"),
    tools=[nyc_dataset_tool, tool],  # Add here
    instruction="..."
)
```

### Frontend Feature

1. Edit `frontend/app.js` for new interactions
2. Update `frontend/style.css` for styling
3. Maintain design language (Instrument Serif + DM Sans)

### Agent Instructions

Edit instruction field in `backend/civic_agent/agent.py`:

```python
agent = Agent(
    name="civic_algorithm_agent",
    model=os.getenv("DEMO_AGENT_MODEL"),
    tools=[nyc_dataset_tool],
    instruction="""Your instructions here..."""
)
```

## Code Quality

### Linting

```bash
uv run --project backend ruff check .           # Check issues
uv run --project backend ruff check --fix .     # Auto-fix
```

### Formatting

```bash
uv run --project backend ruff format .
```

### Type Checking

```bash
uv add --project backend --dev mypy
uv run --project backend mypy backend/
```

## Testing

### Run Tests

```bash
uv run --project backend pytest                      # All tests
uv run --project backend pytest tests/test_agent.py  # Specific file
uv run --project backend pytest --cov=backend        # With coverage
```

### Write Tests

Create in `backend/tests/`:

```python
import pytest
from civic_agent.agent import query_nyc_dataset

@pytest.mark.asyncio
async def test_dataset_query():
    result = await query_nyc_dataset("What tools does NYPD use?")
    assert "NYPD" in result
    assert len(result) > 0
```

## Debugging

### Backend

Debug logging is enabled by default. View logs in terminal running uvicorn.

### Frontend

Open DevTools (F12):
- **Console:** JavaScript logs and errors
- **Network:** WebSocket frames
- **Application:** Permissions and media devices

### Audio Pipeline

Test microphone in browser console:

```javascript
navigator.mediaDevices.getUserMedia({ audio: true })
  .then(stream => console.log('Microphone OK'))
  .catch(err => console.error('Error:', err));
```

### WebSocket

Test with wscat:

```bash
npm install -g wscat
wscat -c "ws://localhost:8000/ws/test-user/test-session"
> {"type": "text", "text": "hello"}
```

## Common Tasks

### View Dependency Tree

```bash
uv tree --project backend
```

### Check Security

```bash
uv add --project backend --dev safety
uv run --project backend safety check
```

### Test Dataset Query

```bash
uv run --project backend python -c "
import asyncio
from civic_agent.agent import query_nyc_dataset

async def test():
    result = await query_nyc_dataset('What tools does NYPD use?')
    print(result)

asyncio.run(test())
"
```

## Architecture Notes

**UV workspace:** Clean separation, shared lockfile, scalable

**ADK vs direct API:** Session management, streaming, tool calling abstraction

**Keyword retrieval:** Fast (<100ms), no ML overhead, good for MVP. Consider vector embeddings for semantic search later.

**WebSocket:** Bi-directional streaming, binary audio support, lower latency than SSE
