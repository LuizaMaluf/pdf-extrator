FROM python:3.12-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
    ghostscript \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install uv

# ── deps ──────────────────────────────────────────────────────────────────────
FROM base AS deps

WORKDIR /app
COPY pyproject.toml ./
RUN uv pip install --system --no-cache ".[dev]" 2>/dev/null || uv pip install --system --no-cache .

# ── app ───────────────────────────────────────────────────────────────────────
FROM deps AS app

WORKDIR /app
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini ./

RUN mkdir -p /app/uploads

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
