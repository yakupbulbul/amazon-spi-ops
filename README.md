# Amazon Seller Ops

Production-minded full-stack application for Amazon seller operations. Phase 1 establishes the
repository, backend and frontend scaffolds, Dramatiq worker wiring, Docker topology, and a
responsive admin shell with live backend health status.

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

The frontend expects the backend at `http://localhost:8000/api` during local development. In
Docker, `VITE_API_BASE_URL` is set to `/api` and routed through Nginx.

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
- backend `pytest`
- backend `mypy app`
- backend live health requests to `/api/health` and `/api/health/ready`
- frontend `npm run lint`
- frontend `npm run build`
- `docker compose config`

Not fully verified in this environment:

- `docker compose up --build`

The Docker startup check was blocked because the local Docker daemon socket was unavailable at
`/Users/yakupbulbul/.docker/run/docker.sock`.
