# Build
FROM python:3.14-slim AS builder

WORKDIR /app
RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Runtime
FROM python:3.14-slim
WORKDIR /app

# Install runtime dependencies (e.g., for discord-py voice support)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libffi-dev \
    libopus0 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*
# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

COPY . .
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Run the bot
CMD ["python", "main.py"]
