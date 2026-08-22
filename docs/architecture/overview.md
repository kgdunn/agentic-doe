# System Architecture

Cross-repo system architecture for the Factorial platform.

## Product Overview

A conversational, LLM-assisted web application that helps users design, run, and analyze scientific experiments using Design of Experiments (DOE) methodology. The agent (powered by the Anthropic API) is the primary mode of interaction — it challenges user designs, advises on alternatives, and guides analysis.

### Key Features

- **User signup** with role/background selection
- **Agent-first chat UI** as the primary interaction mode
- **Experiment design** via conversational agent (factorial, RSM, optimal, mixture, screening)
- **Incremental results entry** — users enter results as they become available
- **Partial and full analysis** of experimental results
- **Interactive visualization** — the main differentiator (3D response surfaces, contour plots, interaction plots)
- **Model save/share** — save models and share publicly

## Architecture Diagram

```
┌─────────────────────────────────────────────────────┐
│                  FastAPI + Uvicorn                  │
│  ┌───────────┐  ┌───────────┐  ┌────────────────┐   │
│  │ /api/v1/  │  │ Pydantic  │  │   Middleware   │   │
│  │ endpoints │  │ schemas   │  │ (CORS, etc.)   │   │
│  └─────┬─────┘  └───────────┘  └────────────────┘   │
│        │                                            │
│  ┌─────▼──────────────┐                            │
│  │ SQLAlchemy async   │                            │
│  │ (get_db_session)   │                            │
│  └─────┬──────────────┘                            │
└────────┼───────────────────────────────────────────┘
         │
    ┌────▼─────┐
    │ Postgres │
    │    16    │
    └──────────┘

┌─────────────────────────────────────────────────────┐
│             SvelteKit (Static Adapter)              │
│  ┌───────────┐  ┌───────────┐  ┌────────────────┐   │
│  │ Routes    │  │ Components│  │ Stores         │   │
│  │ (pages)   │  │ (Svelte5) │  │ (state mgmt)   │   │
│  └───────────┘  └───────────┘  └────────────────┘   │
│                     │                               │
│              fetch /api/v1/*                        │
└─────────────────────┼───────────────────────────────┘
                      │ HTTP
                      ▼
              FastAPI backend
```

## Health Endpoints

- `GET /api/v1/health` — Liveness probe (is the API process running?)
- `GET /api/v1/health/ready` — Readiness probe (is PostgreSQL connected?)

## Docker Compose Services

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| app | Custom (backend/Dockerfile) | 8000 | FastAPI backend |
| frontend | Custom (frontend/Dockerfile) | 3000 (→80) | SvelteKit via nginx |
| postgres | postgres:16-alpine | 5432 | Relational storage |
| redis | redis:7-alpine (deferred) | 6379 | Sessions/caching |

## Deployment Target

**Linux VPS** running docker-compose. Single server for MVP.

Graduation path:

- Phase 1 (MVP): Single VPS with docker-compose
- Phase 2: Managed PostgreSQL, static assets via CDN
- Phase 3: Container orchestration
