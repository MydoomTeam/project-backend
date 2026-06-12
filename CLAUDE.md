# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

ArenaSync is a monolithic FastAPI + SQLAlchemy 2.0 backend (PostgreSQL 16 in Docker)
for managing game tournaments: player registration/login, four elimination formats,
bracket generation, match results, and an adaptive ELO system.

## Commands

```bash
# Start the database (Docker), then the API server
docker compose up -d
uvicorn app.main:app --reload --app-dir src   # docs at http://localhost:8000/docs

# Run all tests (pytest.ini sets pythonpath=src, testpaths=tests)
pytest

# Run one file / class / test
pytest tests/unit/test_match_algorithms.py
pytest tests/unit/test_match_service.py::TestRanking
pytest tests/unit/test_match_algorithms.py::test_name -q

# Database migrations (alembic.ini at repo root)
alembic upgrade head
alembic revision --autogenerate -m "message"

# One-off helpers
python scripts/reset_db.py
python scripts/seed_overdue_postgres.py
```

First-time setup is automated by `setup.bat` (Windows) / `setup.sh` (Linux/macOS):
docker up, venv, `pip install -r requirements.txt`, copy `.env.example` → `.env`.

## Environment

`.env` requires `DATABASE_URL` (must match `docker-compose.yml` credentials) and
optionally `AUTH_SECRET`. Defaults live in `src/app/core/config.py` (`Settings` dataclass).

## Architecture

The codebase currently contains two functional stacks that coexist in the same repository.

### Tournament stack (newer)

Main flow:

api/tournaments.py
→ services/{tournament,match,registration}_service.py
→ repositories/*_repository.py
→ models/{tournament,match,registration,audit_log}.py
→ schemas/*

Responsibilities:

- tournaments,
- registrations,
- matches,
- rankings,
- ELO calculations.

### Administrative stack (original)

Main flow:

controllers/{jugador,admin,alerta,health}_controller.py
→ services/{jugador,admin,alerta}_service.py
→ repositories/*
→ domain/models/*
→ domain/schemas/*

Responsibilities:

- player management,
- authentication,
- administration,
- alerts,
- history and audit information.

### Architectural rule

Expected dependency flow:

Controller / Router
→ Service
→ Repository
→ Database

Repositories are responsible only for data access.

Services are responsible for business logic and use-case orchestration.

Controllers and routers are responsible only for HTTP concerns.

### Important notes

- The repository contains both English and Spanish modules.
- Similar business concepts may exist in both stacks.
- Do not assume that similarly named models represent the same database table.
- Before refactoring, verify which implementation is actually used by the active services and repositories.
- Treat duplicated concepts as a migration and consolidation risk, not as proof of a defect.

### Current behavior

Services currently raise `HTTPException` directly.

When auditing architecture:

- report this behavior,
- evaluate whether it is acceptable,
- do not change it automatically,
- only refactor it if exception handling is an explicit objective of the current task.

### App startup (`src/app/main.py`)

`lifespan` seeds a system admin (`SYSTEM_ADMIN_ID = 1`, used as the actor for audit
logs) and starts the APScheduler. `Base.metadata.create_all` runs on import, and all
model modules must be imported there so their tables register. A custom
`RequestValidationError` handler returns `422` with
`{"detail": {"error": "validation_error", "details": [...]}}`.

### Auth (`src/app/core/auth.py`)

Tokens are **not JWT** — a custom `base64(payload).hmac_sha256` scheme signed with
`AUTH_SECRET`. `get_current_user` (FastAPI dependency) reads `Authorization: Bearer`
and returns the integer user id. There are **no roles**: any player can create a
tournament, and the creator becomes its admin (only they generate the bracket, start
it, and record results).

### ELO and tournament formats

ELO logic and format constants live in `services/match_service.py`. Adaptive K-factor:
40 below 1000 ELO, 32 standard, 16 above 2000. Four formats with min-players/max-rounds
constraints: `"Eliminación Sencilla"`, `"Eliminación Doble"`, `"Round Robin"`, `"Swiss"`
(see `_MIN_PARTICIPANTES` and bracket constants in that file). Pure algorithm logic is
covered by `tests/unit/test_match_algorithms.py`.

### Background scheduler (`src/app/tasks/scheduler.py`)

APScheduler `BackgroundScheduler` periodically scans for overdue `Enfrentamiento`
records and writes alerts + audit log entries. It is patched out in tests
(`patch("app.main.start_scheduler", ...)` in `conftest.py`).

## Testing

`tests/conftest.py` overrides `DATABASE_URL` to in-memory SQLite (`StaticPool`),
rebinds `database.engine`/`SessionLocal`, and provides `db_session` and `client`
fixtures. The `client` fixture overrides `get_db`, `get_current_user`, and
`get_current_admin_id` (auth is stubbed to user id 1).

- `tests/unit/` — services and algorithms, mostly DB-free / monkey-patched.
- `tests/integration/` — against in-memory SQLite (UC-01 password, UC-02 alerts, UC-03 tournament).
- `tests/e2e/` — full HTTP via `TestClient`.

## Language Policy

Code identifiers must be written in English:

- file names,
- directory names,
- classes,
- functions,
- methods,
- variables,
- constants,
- enums,
- internal APIs,
- database entity names,
- repository names,
- service names,
- route paths and URL segments.

User-facing text may remain in Spanish:

- validation messages,
- business messages,
- UI responses,
- API messages shown to end users,
- console output intended for users,
- logs intended for operators,
- test descriptions (result),
- project documentation.

Examples:

✅ Good

def calculate_elo():
    pass

return {"mensaje": "Torneo creado correctamente"}

Route:
POST /tournaments

❌ Bad

def calcular_elo():
    pass

POST /torneos

## Project Rules

Before modifying code read:

1. docs/PROJECT_CONTEXT.md
2. docs/ENGLISH_STANDARD.md
3. docs/ARCHITECTURE.md
4. docs/REST_API.md
5. docs/CLEAN_CODE.md
6. docs/REVIEW_PROCESS.md

### Language Rules

Programming identifiers must be in English:
- files
- folders
- classes
- functions
- variables
- constants
- internal schemas

User-facing text may remain in Spanish:
- UI messages
- tournament names
- player names
- visible labels
- business content

Do not translate user-facing content unless explicitly requested.

### Refactoring Rules

- Prefer minimal changes.
- Do not introduce new patterns without need.
- Do not create new layers.
- Preserve current behavior.