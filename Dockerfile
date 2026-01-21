FROM python:3.12-slim

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project files
COPY pyproject.toml .
COPY app/ app/
COPY alembic/ alembic/
COPY alembic.ini .
COPY static/ static/

# Install dependencies
RUN uv pip install --system --no-cache \
    fastapi uvicorn[standard] sqlalchemy[asyncio] asyncpg \
    redis httpx pydantic-settings arq alembic slowapi

EXPOSE 8000

# Startup script that runs migrations then starts the app
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
