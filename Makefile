SHELL := /bin/zsh

.PHONY: install-backend install-frontend dev-backend dev-frontend lint test up down

install-backend:
	cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install --upgrade pip && pip install -e ".[dev]"

install-frontend:
	cd frontend && npm install

dev-backend:
	cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd frontend && npm run dev -- --host 0.0.0.0 --port 5173

lint:
	cd backend && source .venv/bin/activate && ruff check .
	cd frontend && npm run lint

test:
	cd backend && source .venv/bin/activate && pytest

up:
	docker compose up --build

down:
	docker compose down

