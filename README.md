# NutriBot

Conversational nutrition assistant over Telegram, with a Python backend, RAG over
DeepSeek, and two dashboards (client + admin). Personal project, built in phases.

## Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Alembic
- **Database:** PostgreSQL 16 + pgvector
- **Bot:** python-telegram-bot (async)
- **AI:** DeepSeek API (OpenAI-compatible) with function calling
- **RAG:** pgvector + local embeddings (bge-m3)
- **Nutrition data:** Open Food Facts API (cached in Postgres)
- **Frontends:** React + Vite + TypeScript + TailwindCSS
- **Tooling:** uv (Python), pnpm (frontend), Docker Compose

## Features

- Telegram bot with **consent gate** + guided **onboarding** (button-driven profile).
- Conversational chat over DeepSeek, personalized with the user's profile.
- **RAG**: knowledge documents chunked + embedded (bge-m3) and injected as context.
- **Function calling**: food lookups via Open Food Facts (name/barcode, cached),
  meal logging and daily macro tracking.
- **Client dashboard**: login via Telegram code, profile, macro/weight charts,
  conversation history.
- **Admin dashboard**: user management, RAG document management, editable legal
  text, and DeepSeek token/cost metrics.

## Getting started (development)

```bash
# 1. Create your env file and fill in secrets
cp .env.example .env
#    Set DEEPSEEK_API_KEY, TELEGRAM_BOT_TOKEN, and a JWT_SECRET:
#    python -c "import secrets; print(secrets.token_hex(32))"

# 2. Start the whole stack (Postgres+pgvector, embeddings, backend, bot, dashboards)
docker compose up --build

# 3. Apply migrations
docker compose run --rm backend uv run alembic upgrade head

# 4. Create an admin user (for the admin dashboard)
docker compose run --rm backend uv run python scripts/create_admin.py \
  admin@example.com "your-password" "Admin"
```

- API docs: http://localhost:8000/docs
- Client dashboard: http://localhost:5173
- Admin dashboard: http://localhost:5174

## Deployment

See **[DEPLOY.md](DEPLOY.md)** for a production setup on a VPS (Docker Compose +
Caddy with automatic HTTPS).

## Repository layout

```
nutribot/
├── backend/            # FastAPI app (API, services, models, migrations)
├── bot/                # Telegram bot (python-telegram-bot, polling)
├── dashboard-client/   # React + Vite client dashboard
├── dashboard-admin/    # React + Vite admin dashboard
├── docker-compose.yml         # development
├── docker-compose.prod.yml    # production (VPS)
├── Caddyfile                  # reverse proxy / TLS (prod)
├── DEPLOY.md
└── README.md
```
