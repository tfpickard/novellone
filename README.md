# Hurl Unmasks Recursive Literature Leaking Out Light

Autonomous science-fiction narratives that write, edit, score, and style themselves in real time. Hurl Unmasks Recursive Literature Leaking Out Light orchestrates a pool of AI-authored tales, continuously generating chapters, evaluating quality, and presenting each story with bespoke visual theming.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Core Features](#core-features)
3. [Architecture](#architecture)
4. [Story Lifecycle](#story-lifecycle)
5. [Backend Services](#backend-services)
6. [Frontend Application](#frontend-application)
7. [Getting Started](#getting-started)
8. [Configuration](#configuration)
9. [Running the Stack](#running-the-stack)
10. [Development Workflow](#development-workflow)
11. [Data Model](#data-model)
12. [API Surface](#api-surface)
13. [Background Worker](#background-worker)
14. [Observability & Logs](#observability--logs)
15. [Troubleshooting](#troubleshooting)
16. [Contributing](#contributing)
17. [License](#license)

---

## Project Overview

Hurl Unmasks Recursive Literature Leaking Out Light is a containerized platform built to explore autonomous storytelling. It generates multiple science-fiction stories simultaneously, lets them evolve chapter-by-chapter, evaluates their quality, and gracefully retires narratives that fall below expectations. The result is a living catalog of endlessly changing tales, each with unique aesthetics and a shared canon character named Tom—the tinkering engineer who anchors every premise.

---

## Core Features

- **Autonomous Story Pool** – Keeps the number of active stories between configurable minimum and maximum bounds.
- **AI Story Generation** – Uses OpenAI Chat Completions for premises, chapters, themes, and critical evaluations.
- **Chaos Parameters** – Assigns seeded absurdity/surrealism/ridiculousness/insanity values that grow with each chapter.
- **Quality Evaluation Loop** – Scores coherence, novelty, engagement, and pacing. Stories that fall below `quality_score_min` are concluded.
- **Cover Art Synthesis** – Generates DALL·E book covers automatically when a story completes.
- **Live Updates** – Uses WebSockets to push new chapters/completions to connected clients.
- **Visual Theming** – Applies per-story CSS variables (colors, fonts, animations) sourced from AI-generated theme JSON.
- **Story Intelligence Dashboards** – Interactive timeline + “DNA” radar views surface pacing, chaos vectors, and evaluation health for each narrative.
- **Markdown-native Chapters** – Premises and chapters are authored in Markdown and rendered with sanitized HTML in the reader.
- **Runtime Configuration** – Adjustable pacing, evaluation cadence, and context windows through a secure, password-protected admin UI.
- **Secure Admin Console** – Cookie-based authentication with signed sessions guards destructive controls.
- **Statistical Dashboards** – Aggregates story counts, chapter totals, token usage, average chaos levels, and recent activity.

---

## Architecture

```
┌──────────────┐       ┌────────────────────┐       ┌─────────────┐
│  Frontend    │  WS   │   FastAPI Backend  │  SQL  │  PostgreSQL │
│  (SvelteKit) │◀─────▶│   REST + WebSocket │◀─────▶│   Database  │
└──────┬───────┘       └─────────┬──────────┘       └──────┬──────┘
       │                         │                         │
       │  REST /api/*            │  Background Worker       │
       │                         ▼                         │
       │                Story Generator (OpenAI)           │
       │                Story Evaluator (OpenAI)           │
       ▼
Browser renders live stories with per-story theming,
timelines, and stats dashboards.
```

### Technology Stack

- **Frontend**: [SvelteKit](https://kit.svelte.dev/) + TypeScript + Vite
- **Backend**: [FastAPI](https://fastapi.tiangolo.com/) + SQLAlchemy (async) + APScheduler
- **Database**: PostgreSQL 16 with JSONB support
- **Task Orchestration**: Background worker loop triggered by APScheduler
- **AI Providers**: OpenAI Chat Completions + Images API
- **Deployment**: Docker Compose with three services (backend, frontend, database)

---

## Story Lifecycle

1. **Spawn** – The background worker ensures at least `min_active_stories` exist. If at capacity, it gracefully completes the oldest active story to free a slot.
2. **Premise & Theme** – `story_generator.spawn_new_story` requests a novel premise + theme JSON, seeding chaos parameters.
3. **Chapter Generation** – At every `chapter_interval_seconds`, active stories receive new chapters that escalate absurdity coefficients.
4. **Quality Evaluation** – Every `evaluation_interval_chapters`, stories are scored via `story_evaluator.evaluate_story`.
5. **Completion** – Stories terminate when quality dips below the threshold, reach `max_chapters_per_story`, or are manually killed.
6. **Cover Art** – Completed stories without cover art trigger a DALL·E request to synthesize a themed book cover.
7. **Replacement** – Newly completed stories are removed from the active pool, allowing fresh narratives to spawn.

---

## Backend Services

Located under `backend/` and exposed as a FastAPI app (`main.py`):

- **REST API** (`/api/*`): CRUD for stories, runtime configuration, statistics, admin actions.
- **WebSocket Gateway** (`/ws/stories`): Broadcasts `new_chapter`, `story_completed`, and `system_reset` events.
- **Background Worker** (`background_worker.py`): APScheduler-based loop that drives chapter generation and evaluations.
- **Story Generator** (`story_generator.py`): OpenAI prompt orchestration to fabricate premises, chapters, and cover art featuring the story title typography.
- **Story Evaluator** (`story_evaluator.py`): Determines if narratives should continue based on weighted metrics.
- **Config Store** (`config_store.py`): Persists runtime tuning values in the database.
- **Database** (`database.py` + `models.py`): Async SQLAlchemy with Alembic migrations in `backend/alembic/`.

Environment configuration is managed via `backend/config.py`, which loads `.env` variables into Pydantic settings.

---

## Frontend Application

Found under `frontend/`, implemented with SvelteKit:

- **Routes**
  - `/` – Story index with featured cover gallery, status filters, smart sorting, and admin controls.
  - `/story/[id]` – Detailed live view with rendered Markdown chapters, story timeline, DNA radar, and evaluation metadata.
  - `/config` – Runtime configuration editor for administrators.
  - `/login` – Session-based admin sign-in that unlocks protected controls.
  - `/stats` – Aggregate metrics, chapter feed, and chaos averages.
- **Libraries**
  - `$lib/api` – Fetch abstraction for backend endpoints.
  - `$lib/theme` – Applies AI-provided theme variables to DOM nodes.
  - `$lib/websocket` – Creates resilient WebSocket connections with exponential backoff.
  - `$lib/markdown` – Sanitizes and renders Markdown responses into HTML for the reader.
- **Styling**
  - Tailored CSS-in-component styles leveraging theme CSS variables.

The frontend expects a proxy or CORS-enabled backend reachable at `http://<host>:8000`. In Docker Compose, services communicate over the internal network.

---

## Getting Started

### Prerequisites

- Docker & Docker Compose **or**:
  - Python 3.11+
  - Node.js 18+
  - PostgreSQL 16+
- OpenAI API key with access to the configured Chat & Images models.

### Clone the Repository

```bash
git clone https://github.com/your-org/novellone.git
cd novellone
```

---

## Configuration

1. Copy the sample environment file and adjust:

   ```bash
   cp .env.example .env
   ```

2. Key variables:

   | Variable | Description |
   | --- | --- |
   | `OPENAI_API_KEY` | API key used by story generator/evaluator |
   | `OPENAI_MODEL` | Primary chat completion model for chapters |
   | `OPENAI_PREMISE_MODEL` | Model used for premise + theme generation |
   | `OPENAI_EVAL_MODEL` | Model used to score stories |
   | `OPENAI_MAX_TOKENS_*` | Output token budgets per task |
   | `DATABASE_URL` | Async SQLAlchemy DSN (must include `+asyncpg`) |
   | `WORKER_TICK_INTERVAL` | Seconds between APScheduler ticks |
   | `MIN_CHAPTERS_BEFORE_EVAL` | Chapters before first evaluation |
   | `ENABLE_WEBSOCKET` | Toggle broadcast events |
   | `ADMIN_USERNAME` | Login handle for the protected admin console |
   | `ADMIN_PASSWORD` | Cleartext password (automatically hashed on startup with bcrypt) |
   | `SESSION_SECRET` | Random string used to sign and verify session cookies |
   | `SESSION_TTL_SECONDS` | Session lifetime in seconds (defaults to one week) |
   | `SESSION_COOKIE_NAME` | Optional override for the session cookie name |
   | `SESSION_COOKIE_DOMAIN` | Optional cookie domain (leave blank for same-origin) |
   | `SESSION_COOKIE_SECURE` | Set `true` when serving over HTTPS, otherwise `false` |
   | `SESSION_COOKIE_SAMESITE` | `lax`, `strict`, or `none` depending on proxy setup |

3. Optional overrides can be stored in `backend/config_store.py` via the `/api/config` endpoint.

---

## Running the Stack

### Docker Compose (recommended)

```bash
docker-compose up --build
```

This will:

- Build backend & frontend images
- Apply Alembic migrations on backend start
- Serve FastAPI at `http://localhost:8000`
- Serve SvelteKit frontend at `http://localhost:4000`

### Manual Development

From the project root:

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Frontend (new terminal)
cd frontend
npm install
npm run dev -- --host
```

The frontend development server proxies API calls via `VITE_PUBLIC_API_URL` or falls back to `http://localhost:8000`.

After both services are running, browse to `http://localhost:3000/login` to authenticate before opening the protected `/config` dashboard.

---

## Development Workflow

- **Hot Reloading** – APScheduler worker restarts automatically in development due to `uvicorn --reload`.
- **Database Migrations** – New schema changes require Alembic revisions (`alembic revision --autogenerate -m "message"`).
- **Formatting & Linting** – Configure your editor; repository does not enforce tooling yet.
- **Testing** – Automated tests are not bundled. Consider adding FastAPI, SQLAlchemy, and end-to-end tests for safety.

---

## Data Model

Key tables (see `backend/models.py`):

- `stories`
  - Metadata: title, premise, status, timestamps, cover image URL
  - Chaos parameters: initial + per-chapter increments for absurdity/surrealism/ridiculousness/insanity
  - Relationships: `chapters`, `evaluations`
- `chapters`
  - Chapter number, content, generation metadata, per-chapter chaos readings
- `story_evaluations`
  - Scores for coherence, novelty, engagement, pacing, boolean `should_continue`
  - Evaluation reasoning and issues list (JSONB)
- `system_config`
  - Arbitrary JSON payload keyed by configuration option

---

## API Surface

> Refer to `backend/main.py` for full details.

### Public Endpoints

- `GET /api/stories` – Paginated story list (filter by status)
- `GET /api/stories/{id}` – Story detail with chapters & evaluations
- `GET /api/stats` – Aggregate counters, recent chapters, chaos averages
- `GET /api/config` – Current runtime configuration

### Admin Endpoints

- `POST /api/admin/spawn` – Manually spawn a story (honors max active limit)
- `POST /api/admin/reset` – Purge stories & reset config
- `POST /api/admin/backfill-cover-images` – Generate covers for completed stories

### Story Management

- `POST /api/stories/{id}/kill` – End a story early with optional reason
- `DELETE /api/stories/{id}` – Permanently remove a story

### WebSocket

- `GET /ws/stories`
  - Broadcast messages:
    - `new_story`
    - `new_chapter`
    - `story_completed`
    - `system_reset`

---

## Background Worker

- Runs on `WORKER_TICK_INTERVAL` (default 15 seconds).
- For each active story:
  - Checks if chapter interval elapsed; generates new chapter via OpenAI.
  - Triggers evaluation at configured cadence.
  - Completes stories at max length or on poor quality.
- Maintains active story count, spawning replacements as needed.
- Emits WebSocket events whenever new chapters or completions occur.

---

## Observability & Logs

- Uvicorn logs stream to stdout by default; Docker Compose mounts `./logs/backend`.
- Structured logging configured in `backend/logging_config.py`.
- Background worker logs timing, OpenAI usage, and failure states.
- Consider integrating Prometheus or a log shipper for production deployments.

---

## Troubleshooting

| Symptom | Possible Fix |
| --- | --- |
| `asyncpg` driver errors | Ensure `DATABASE_URL` uses `postgresql+asyncpg://` |
| Stories never spawn | Verify OpenAI credentials and worker logs |
| Cover images missing | Check DALL·E access and network egress |
| Frontend API failures | Set `VITE_PUBLIC_API_URL` or enable CORS |
| WebSocket disconnects | Confirm `ENABLE_WEBSOCKET` and reverse proxy timeouts |

---

## Contributing

1. Fork and clone the repository.
2. Create a feature branch (`git checkout -b feature/my-idea`).
3. Make changes with descriptive commits.
4. Run linting/tests if available.
5. Open a pull request describing motivation, changes, and verification steps.

Feature ideas are welcome—especially around story visualization, interactive storytelling, or safety controls.

---

## License

No explicit license has been provided. All rights reserved unless a license file is added.

---
