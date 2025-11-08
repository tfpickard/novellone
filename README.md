# Eternal Stories

Eternal Stories is a containerized platform that generates and curates multiple autonomous science fiction narratives. The backend orchestrates story lifecycle management, OpenAI-powered generation, and evaluation while the SvelteKit frontend renders real-time updates with bespoke visual themes per story.

## Features

- Maintains a configurable pool of concurrent stories with APScheduler workers
- Uses OpenAI models for premise, chapter, evaluation, and visual theme generation
- Weighted quality scoring with automatic story termination and replacement
- FastAPI REST API and WebSocket channel for live updates
- SvelteKit SPA applying unique story themes via CSS variables
- PostgreSQL persistence with Alembic migrations
- Docker Compose deployment with separate backend, frontend, and database services

## Prerequisites

- Docker and Docker Compose
- OpenAI API key with access to configured models

## Configuration

1. Copy `.env.example` to `.env` at the repository root and populate values:

   ```bash
   cp .env.example .env
   ```

2. Ensure `DATABASE_URL` uses the asyncpg driver (`postgresql+asyncpg://`).
3. Set `OPENAI_API_KEY` and adjust model/temperature/token limits as desired.
4. Tune timing and evaluation thresholds to control narrative pacing.

## Running Locally

```bash
docker-compose up --build
```

This command builds backend and frontend images, applies environment variables from `.env`, and starts PostgreSQL. The backend listens on `http://localhost:8000` and the frontend on `http://localhost:3000`.

## Database Migrations

Alembic configuration lives under `backend/alembic`. To create or apply migrations:

```bash
cd backend
alembic upgrade head
```

Generate a new migration after adjusting SQLAlchemy models:

```bash
alembic revision --autogenerate -m "Your message"
```

## Development Tips

- The backend uses async SQLAlchemy with PostgreSQL; ensure the DSN includes `+asyncpg`.
- APScheduler runs on application startup and respects the `WORKER_TICK_INTERVAL`.
- WebSocket broadcasting can be toggled via `ENABLE_WEBSOCKET`.
- Frontend expects proxying to backend API via `/api/*` when using SvelteKit dev server.

## Testing

Automated tests are not bundled. Consider adding API or end-to-end tests tailored to your infrastructure and OpenAI usage patterns.
