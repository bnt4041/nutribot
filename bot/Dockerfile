# Telegram bot image: Python 3.12 + uv
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Install dependencies (project itself is not packaged; see tool.uv.package = false)
COPY pyproject.toml ./
RUN uv sync

# Copy bot source
COPY . .

CMD ["uv", "run", "python", "main.py"]
