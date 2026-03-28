# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

YOLOv13 RainFog Detection is a full-stack web application for rain/fog weather object detection. It consists of three services:
- **Django backend** (port 8000) — business logic, auth, task management, MySQL persistence
- **FastAPI inference service** (port 9000) — YOLO model execution (currently mock, Phase 4 adds real YOLOv13)
- **React frontend** (port 5173) — admin dashboard UI

## Development Commands

### Infrastructure (MySQL + Redis)
```bash
docker compose -f docker-compose.dev.yml up -d    # start
docker compose -f docker-compose.dev.yml down      # stop
```

### Backend (from `backend/`)
```bash
uv sync                                            # install deps
uv run python manage.py migrate                    # run migrations
uv run python manage.py runserver 0.0.0.0:8000    # Django (port 8000)
uv run uvicorn inference_service.main:app --reload --host 0.0.0.0 --port 9000  # FastAPI
uv run python manage.py createsuperuser           # create admin
```

### Testing & Linting (from `backend/`)
```bash
uv run pytest                          # all tests
uv run pytest tests/path/test_file.py  # single test file
uv run pytest -k "test_name"           # single test by name
uv run ruff check .                    # lint
uv run ruff format .                   # format
```

Test config: `pytest.ini_options` in `pyproject.toml`, `DJANGO_SETTINGS_MODULE=config.settings.dev`, tests in `tests/`.

### Frontend (from `frontend/`)
```bash
npm install
npm run dev      # Vite dev server (port 5173)
npm run build
```

## Architecture

### Request Flow
1. Frontend (React + Zustand auth) → Django `/api/v1/` (Token auth)
2. Django creates task, calls FastAPI `POST /internal/inference/detect`
3. FastAPI runs adapter (mock or YOLOv13) → returns detections
4. Django persists `DetectionTask → InferenceRecord → DetectionObject` in MySQL
5. Frontend displays results on DetectionDetailPage

### Django Apps (`backend/apps/`)
| App | Responsibility |
|-----|----------------|
| `accounts` | Login, token auth, current user |
| `detection` | Task lifecycle (create, status, retry) |
| `media` | Image upload/management |
| `audit` | Operation audit logs |
| `dashboard` | Statistics/metrics |
| `system` | System configuration |

### FastAPI Inference Service (`backend/inference_service/`)
- `api/` — endpoints: `/internal/health`, `/internal/models/current`, `/internal/inference/detect`
- `adapters/` — `mock.py` (default), `yolov13.py` (Phase 4, lazy-loaded), `base.py`
- `services/` — orchestration pipeline
- `core/config.py` — settings via env vars

### Frontend (`frontend/src/`)
- `pages/` — login, dashboard, detection list, detection detail, system, audit
- `router/index.tsx` — protected routes (requires auth token)
- `stores/auth-store.ts` — Zustand auth state
- `features/` — feature-specific logic
- `services/` — API client (calls Django backend)

## Key Environment Variables

Create `backend/.env` based on `.env.example`. Critical vars:
```
INFERENCE_BASE_URL=http://localhost:9000
INFERENCE_MODEL_MODE=mock            # or "yolov13" for Phase 4
INFERENCE_USE_MOCK=true
INFERENCE_YOLOV13_MODEL_FILE=yolov13n.pt
INFERENCE_MODELS_ROOT=../data/models
INFERENCE_YOLOV13_ROOT=../yolov13-main
```

## Enabling Real YOLOv13 (Phase 4)

```bash
# Apple Silicon / Linux / Windows:
cd backend && uv sync --extra yolo

# Intel Mac only (PyTorch special handling):
conda install pytorch torchvision cpuonly -c pytorch && pip install ultralytics
```

Then set `INFERENCE_MODEL_MODE=yolov13` in `.env`. Model files (`.pt`) go in `data/models/`.

## Implementation Status

- **Complete (Phase 2)**: Auth, image upload, detection task CRUD, mock inference, result storage, frontend dashboard/routing
- **In progress (Phase 3)**: Redis caching integration
- **Planned (Phase 4)**: Real YOLOv13 inference (adapter code exists at `inference_service/adapters/yolov13.py`)
- **Planned (Phase 5)**: Celery async task queue

See `docs/02-implementation-roadmap.md` for full phase details and `docs/01-system-design.md` for architecture decisions.
