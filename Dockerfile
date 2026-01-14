FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project files
COPY pyproject.toml .
COPY app/ app/
COPY alembic/ alembic/
COPY alembic.ini .

# Install dependencies
RUN uv pip install --system --no-cache \
    fastapi uvicorn[standard] sqlalchemy[asyncio] asyncpg \
    redis httpx pydantic-settings arq alembic

# Create static directory
RUN mkdir -p static

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
