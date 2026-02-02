# syntax=docker/dockerfile:1
# MCP-HN Dockerfile - Multi-stage uv build
# Based on original erithwik/mcp-hn Docker setup

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS uv

WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1
# Copy from the cache instead of linking (for Docker layer caching)
ENV UV_LINK_MODE=copy

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Copy source code
COPY src/ /app/src/
COPY pyproject.toml README.md /app/

# Install the project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev


# Runtime stage - slim image
FROM python:3.12-slim-bookworm

WORKDIR /app

# Copy virtual environment from builder
COPY --from=uv /app/.venv /app/.venv

# Ensure the virtualenv is activated
ENV PATH="/app/.venv/bin:$PATH"

# Run the MCP server
# Backward compatible: mcp-hn matches original entry point
ENTRYPOINT ["mcp-hn"]
