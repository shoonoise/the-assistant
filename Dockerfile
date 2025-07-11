FROM python:3.13 AS builder

# Install uv from official image (pinned version)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install git with proper cleanup
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Set environment variables
ENV UV_COMPILE_BYTECODE=1

# Copy dependency files first (for better caching)
COPY pyproject.toml uv.lock ./

# Install dependencies (this layer will be cached unless pyproject.toml or uv.lock changes)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project --no-editable

# Copy README.md separately (after dependencies are installed)
COPY README.md ./

# Copy source code
COPY src /app/src

# Install the project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable

FROM python:3.13-slim

WORKDIR /app

# Copy the virtual environment and source code
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src

# Set PATH to use the virtual environment
ENV PATH="/app/.venv/bin:$PATH"

# Single CMD statement
CMD ["uvicorn", "src.the_assistant.main:app", "--host", "0.0.0.0", "--port", "8000"] 
