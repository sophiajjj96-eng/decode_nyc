# Quick Start

Get running in 60 seconds.

## Install and Run

```bash
cd algorithm-explained
uv sync
cp backend/env.example backend/.env
# Edit backend/.env and add your GOOGLE_API_KEY
export SSL_CERT_FILE=$(uv run --project backend python -m certifi)
uv run --project backend uvicorn backend.main:app --reload
```

Open `http://localhost:8000`

## Try It Out

**Text mode:** Type "What algorithmic tools does the NYPD use?" and press Enter

**Voice mode:** Click "Voice" toggle, then "Start Discussion" and speak naturally

## Need Help?

See [Setup Guide](SETUP.md) for detailed installation instructions and troubleshooting.
