# Docker parser directive to use the Dockerfile syntax version 1. 
# This line is used to specify the syntax version for the Dockerfile, which can affect how certain instructions are interpreted and executed.
# syntax=docker/dockerfile:1

# Stage 1 — dependency resolver
# Resolve and install dependencies separately so this layer is cached as long
# as pyproject.toml / uv.lock do not change.

FROM python:3.12-slim AS builder

# Copies the prebuilt uv binary from its official image into the container.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency manifests only (pyproject.toml, uv.lock) — maximise cache reuse
# Code changes does not invalidate this layer (only changes to pyproject.toml or uv.lock), so dependencies are not reinstalled unnecessarily.
COPY pyproject.toml uv.lock ./

# Install production dependencies into an isolated virtual environment.
# --no-dev excludes pytest, ruff, etc.
# --frozen ensures the lock file is respected exactly.
RUN uv sync --frozen --no-dev

# Stage 2 — runtime image

FROM python:3.12-slim AS runtime

# Create a non-root user named "app" in a group "app" for security.
# Otherwise, the application would run as root, which is a security risk.
RUN addgroup --system app && adduser --system --ingroup app app

WORKDIR /app

# Copy the virtual environment (i.e., the installed dependencies) from the builder stage
COPY --from=builder /app/.venv /app/.venv

# Copy application source
COPY src/           ./src/
COPY mcp_server/    ./mcp_server/
COPY knowledge-base/ ./knowledge-base/
COPY faiss_index/   ./faiss_index/
COPY api.py         ./api.py

# Ensure the venv binaries are on PATH
# Without this, container would use the system Python and not the venv Python, which would result in missing dependencies.
ENV PATH="/app/.venv/bin:$PATH"

# The app reads OPENAI_API_KEY from the environment — do NOT bake secrets into
# the image. Pass them at runtime with --env or an env file.
ENV PYTHONUNBUFFERED=1

# Switch to non-root user
USER app

EXPOSE 8000

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
