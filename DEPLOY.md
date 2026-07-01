# Despliegue en un VPS

Guía para instalar NutriBot en un servidor propio con Docker y HTTPS automático
(Caddy + Let's Encrypt).

## Requisitos

- Un VPS con **Docker** y **Docker Compose v2** instalados.
- **Al menos 4 GB de RAM** (el modelo de embeddings bge-m3 consume ~2-3 GB).
- Un **dominio** y capacidad de crear registros DNS.
- Puertos **80** y **443** abiertos en el firewall.

## 1. DNS

Crea tres registros `A` (o `CNAME`) apuntando a la IP del VPS:

| Subdominio            | Uso                 |
| --------------------- | ------------------- |
| `app.tudominio.com`   | Dashboard cliente   |
| `admin.tudominio.com` | Dashboard admin     |
| `api.tudominio.com`   | API del backend     |

## 2. Clonar y configurar

```bash
git clone https://github.com/bnt4041/nutribot.git
cd nutribot

cp .env.prod.example .env
nano .env   # rellena secretos y dominios
```

Rellena en `.env`:
- `POSTGRES_PASSWORD` (una contraseña fuerte) y ajusta `DATABASE_URL` con esa misma.
- `DEEPSEEK_API_KEY`, `TELEGRAM_BOT_TOKEN`.
- `JWT_SECRET` → genéralo con:
  ```bash
  docker run --rm python:3.12-slim python -c "import secrets; print(secrets.token_hex(32))"
  ```
- `APP_DOMAIN`, `ADMIN_DOMAIN`, `API_DOMAIN`, `ACME_EMAIL`.

## 3. Levantar el stack

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

La primera vez, el servicio `embeddings` descarga el modelo (~2 GB); espera a que
esté `healthy`:

```bash
docker compose -f docker-compose.prod.yml ps
```

Caddy obtendrá los certificados TLS automáticamente al recibir tráfico en los
dominios.

## 4. Migraciones de base de datos

```bash
docker compose -f docker-compose.prod.yml run --rm backend uv run alembic upgrade head
```

## 5. Crear el usuario administrador

```bash
docker compose -f docker-compose.prod.yml run --rm backend \
  uv run python scripts/create_admin.py tu-email@dominio.com "TU_PASSWORD" "Tu Nombre"
```

## 6. (Opcional) Cargar documentos RAG de ejemplo

```bash
docker compose -f docker-compose.prod.yml exec backend \
  uv run python scripts/load_sample_docs.py http://localhost:8000
```

O súbelos desde el dashboard admin (sección **Documentos RAG**).

## 7. Comprobar

- Cliente: `https://app.tudominio.com`
- Admin: `https://admin.tudominio.com` (entra con el admin del paso 5)
- API/health: `https://api.tudominio.com/api/v1/health`
- Bot: escribe a tu bot en Telegram.

## Actualizar a una nueva versión

```bash
git pull
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml run --rm backend uv run alembic upgrade head
```

## Notas

- **Backups**: haz copia del volumen `pgdata` (datos) periódicamente.
- **RAM insuficiente**: si el contenedor `embeddings` muere con código 137 (OOM),
  amplía la RAM del VPS o baja `--max-batch-tokens` en `docker-compose.prod.yml`.
- **Logs**: `docker compose -f docker-compose.prod.yml logs -f <servicio>`.
- El polling del bot funciona sin exponer nada; no necesita dominio propio.
