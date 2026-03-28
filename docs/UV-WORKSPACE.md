# UV Workspace Setup Complete

## Structure

Successfully converted algorithm-explained to use proper uv workspace pattern:

```
algorithm-explained/               (workspace root)
├── pyproject.toml                (workspace definition)
├── uv.lock                       (shared lockfile - 129 packages)
├── .venv/                        (shared virtual environment)
├── backend/                      (Python subproject)
│   ├── pyproject.toml           (backend dependencies)
│   ├── main.py
│   └── civic_agent/
└── frontend/                     (static files)
```

## Key Changes

### Root pyproject.toml
```toml
[tool.uv.workspace]
members = ["backend"]

[tool.uv]
dev-dependencies = []
```

No `[project]` section - workspace roots only define membership.

### Backend pyproject.toml
```toml
[project]
name = "algorithm-explained-backend"
version = "0.1.0"
description = "Multimodal civic AI agent backend with ADK"
requires-python = ">=3.13"
dependencies = [
    "google-adk>=1.20.0",
    "fastapi>=0.115.0",
    "python-dotenv>=1.0.0",
    "uvicorn[standard]>=0.32.0",
    "httpx>=0.27.0",
]
```

Backend is now an independent subproject within the workspace.

## Commands

### Installation
```bash
# From workspace root - installs all workspace members
uv sync
```

### Running Backend
```bash
# Option 1: From workspace root
uv run --project backend uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Option 2: From backend directory
cd backend
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Managing Dependencies
```bash
# Add dependency to backend
uv add --project backend package-name

# Remove dependency
uv remove --project backend package-name

# View dependency tree
uv tree --project backend
```

## Verification

Tested workspace structure:

```bash
✓ uv sync                                    # Resolved 129 packages
✓ uv tree --project backend                  # Shows backend dependencies
✓ Agent import verification                  # civic_algorithm_agent loads
✓ Model verification                         # gemini-2.5-flash-native-audio
✓ Tool verification                          # 1 tool (query_nyc_dataset)
```

## Benefits

1. **Clean separation**: Backend is independent Python package
2. **Shared lockfile**: Single `uv.lock` ensures consistent versions across subprojects
3. **Scalable**: Easy to add more subprojects (e.g., CLI, workers, tests)
4. **Standard pattern**: Follows uv workspace conventions
5. **Better imports**: Backend modules properly scoped

## Next Steps

### Run the Application

```bash
cd algorithm-explained
uv sync
uv run --project backend uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### Configure API Key

```bash
cp backend/env.example backend/.env
# Add your GOOGLE_API_KEY to backend/.env
```

### Set SSL Certificate

```bash
export SSL_CERT_FILE=$(uv run --project backend python -m certifi)
```

### Test Voice Mode

1. Open `http://localhost:8000`
2. Click "Voice" toggle
3. Click "Start Discussion"
4. Grant microphone permissions
5. Speak: "What algorithmic tools does the NYPD use?"

## Bug Fixes Applied

### Import Error Fix
Changed `from google.adk.functions import FunctionTool` to `from google.adk.tools import FunctionTool` - the correct import path in ADK Python SDK.

### FunctionTool API Fix
Changed from:
```python
FunctionTool(function=query_nyc_dataset, name="...", description="...")
```

To:
```python
FunctionTool(query_nyc_dataset)
```

FunctionTool automatically extracts name, description, and schema from the function's docstring and type hints.

## Documentation Updated

- README.md - Updated installation and running commands
- docs/QUICKSTART.md - Updated with workspace commands
- .gitignore - Added workspace patterns (.venv/, .python-version)

## Workspace Status

Ready for development. All imports verified, workspace properly configured, backend subproject functional.
