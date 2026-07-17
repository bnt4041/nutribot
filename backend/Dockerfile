# Backend image: Python 3.12 + uv for dependency management
FROM python:3.12-slim

# Install system deps: DejaVu fonts for PDF reports (Unicode/emoji support),
# cron to run the reminders job (the "cron" compose service reuses this image).
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-dejavu-core \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Install uv (fast Python package manager)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Install dependencies first (better layer caching)
COPY pyproject.toml ./
RUN uv sync --no-install-project

# Copy application code and migration tooling
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini
COPY scripts ./scripts
COPY sample_docs ./sample_docs

# Install the project itself
RUN uv sync

# Reminders cron job: only active in the "cron" compose service (which
# overrides CMD to `cron -f`); harmless in the API container otherwise.
COPY crontab /etc/cron.d/nutribot-cron
RUN chmod 0644 /etc/cron.d/nutribot-cron && crontab /etc/cron.d/nutribot-cron

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
