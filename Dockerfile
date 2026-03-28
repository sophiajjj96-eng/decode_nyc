FROM python:3.13-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock ./
COPY backend/pyproject.toml backend/

# Install dependencies (no cache, production only)
RUN uv sync --frozen --no-cache --no-dev

# Copy application code
COPY backend/ backend/
COPY frontend/ frontend/

# Cloud Run expects PORT env variable
ENV PORT=8080

# Run with production server
CMD uv run --project backend uvicorn backend.main:app --host 0.0.0.0 --port ${PORT} --workers 1
