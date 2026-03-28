# Amazon Seller Ops

Production-minded full-stack application for Amazon seller operations.

## Phase 1 Scope

- standalone repository scaffold
- FastAPI backend skeleton
- React admin frontend skeleton
- Docker Compose with PostgreSQL, Redis, worker, and Nginx

## Planned Structure

```text
amazon-spi/
├── backend/
├── frontend/
├── nginx/
├── infra/
├── .env.example
├── .gitignore
├── Makefile
└── README.md
```

## Environment Variables

The repository includes placeholders for:

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

Detailed setup instructions will be completed by the end of Phase 1.

