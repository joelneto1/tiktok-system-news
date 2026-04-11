# ── Stage 1: base ──────────────────────────────────────────────
FROM python:3.12-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg \
    ffmpeg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Stage 2: backend-deps ─────────────────────────────────────
FROM base AS backend-deps

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# ── Stage 3: backend ──────────────────────────────────────────
FROM backend-deps AS backend

COPY backend/ ./backend/
COPY alembic/ ./alembic/
COPY alembic.ini ./

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ── Stage 4: worker ───────────────────────────────────────────
FROM backend-deps AS worker

COPY backend/ ./backend/

CMD ["celery", "-A", "backend.worker.celery_app", "worker", "--loglevel=info"]
