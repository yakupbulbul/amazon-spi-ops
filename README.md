# Amazon Seller Ops

Production-minded full-stack application for Amazon seller operations. The current build includes:

- Amazon seller catalog import via SP-API Listings Items
- inventory monitoring with manual sync and low-stock alerts
- price and stock mutation workflows with audit logs
- OpenAI-backed A+ draft generation and publish-payload preview
- Slack notification queueing, worker delivery, and history UI
- responsive admin dashboard, products, inventory, notifications, settings, and A+ Studio pages

## Project Structure

```text
amazon-spi/
├── backend/                # FastAPI app, worker bootstrap, tests
├── frontend/               # React + Vite + Tailwind admin UI
├── nginx/                  # Reverse proxy configuration
├── infra/                  # Reserved for later infrastructure assets
├── .env.example
├── .gitignore
├── Makefile
├── README.md
└── docker-compose.yml
```

## Environment Variables

Copy the template before running locally:

```bash
cp .env.example .env
```

Supported variables:

- `NGINX_PORT`
- `LWA_CLIENT_ID`
- `LWA_CLIENT_SECRET`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `LWA_REFRESH_TOKEN`
- `MARKETPLACE_ID`
- `SELLER_ID`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `SLACK_WEBHOOK_URL`
- `DATABASE_URL`
- `REDIS_URL`
- `SECRET_KEY`
- `APP_ENV`

## Local Development

### Backend

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health endpoints:

```bash
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/health/ready
```

### Frontend

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

The frontend uses same-origin `/api` requests by default. For local Vite development, the dev
server proxies `/api` to `http://localhost:8000`, so the browser does not need CORS enabled. In
other environments, set `VITE_API_BASE_URL` only if you need to override that default.

## Current Application Surface

Default Docker URL:

```text
http://127.0.0.1:8080
```

Default admin login for local development:

```text
admin@example.com
change-me-admin
```

Key UI routes:

- `/`
- `/products`
- `/aplus`
- `/inventory`
- `/notifications`
- `/settings`

Key API routes currently wired:

- `GET /api/health`
- `GET /api/health/ready`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `GET /api/dashboard/summary`
- `GET /api/products`
- `POST /api/products/import`
- `GET /api/products/import-jobs/latest`
- `PATCH /api/products/{id}/price`
- `PATCH /api/products/{id}/stock`
- `GET /api/inventory`
- `GET /api/inventory/alerts`
- `POST /api/inventory/sync`
- `GET /api/aplus/drafts`
- `POST /api/aplus/generate`
- `POST /api/aplus/validate`
- `POST /api/aplus/publish`
- `GET /api/events`
- `POST /api/notifications/slack/test`

## Integration Notes

Amazon SP-API:

- catalog import uses the configured `MARKETPLACE_ID` and `SELLER_ID`
- live inventory sync uses the configured marketplace
- price and stock mutations call the live listing adapter when credentials are present

OpenAI:

- A+ generation uses `OPENAI_API_KEY`
- default model is `gpt-4o-mini`
- if `OPENAI_API_KEY` is unset, the backend returns a deterministic mock draft for local development

Slack:

- Slack delivery is processed asynchronously by the Dramatiq worker
- if `SLACK_WEBHOOK_URL` is unset, notification attempts are recorded as failed with a clear error message
- use the Settings page to queue a test notification and inspect the stored result

## Quality Checks

### Backend

```bash
cd backend
source .venv/bin/activate
ruff check .
pytest
mypy app
```

### Frontend

```bash
cd frontend
npm run lint
npm run build
```

## Docker

Start the full stack:

```bash
docker compose up --build
```

Run in the background:

```bash
docker compose up --build -d
```

Stop the stack:

```bash
docker compose down
```

Services defined in Compose:

- `postgres`
- `redis`
- `backend`
- `worker`
- `frontend`
- `nginx`

By default, Nginx is published on `http://localhost:8080`. Override `NGINX_PORT` in `.env` if you
need a different host port.

## Verification Notes

Verified in this environment:

- backend `ruff check .`
- backend `mypy app`
- backend live health requests to `/api/health` and `/api/health/ready`
- frontend `npm run lint`
- frontend `npm run build`
- `docker compose config`
- `docker compose up --build -d`
- live Amazon catalog import through `/api/products/import`
- live A+ draft generation, validation, and publish-payload preview
- notification queueing through `/api/notifications/slack/test`

Host-side `pytest` may require local installation of `psycopg` if you are not running tests inside
the project backend environment or container.
