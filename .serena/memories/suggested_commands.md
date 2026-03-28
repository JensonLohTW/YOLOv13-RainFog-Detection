# Suggested Commands

## Infrastructure
```bash
docker compose -f docker-compose.dev.yml up -d     # Start MySQL 8.4 + Redis 7.4
docker compose -f docker-compose.dev.yml down       # Stop
```

## Backend (run from `backend/`)
```bash
uv sync                                             # Install Python dependencies
uv sync --extra yolo                                # + real YOLOv13 (Phase 4, non-Intel Mac)
uv run python manage.py migrate                     # Apply DB migrations
uv run python manage.py runserver 0.0.0.0:8000      # Django backend (port 8000)
uv run uvicorn inference_service.main:app --reload --host 0.0.0.0 --port 9000  # FastAPI inference (port 9000)
uv run python manage.py createsuperuser             # Create admin user
uv run python manage.py makemigrations <app>        # Create new migration
```

## Testing (from `backend/`)
```bash
uv run pytest                                       # All tests
uv run pytest tests/path/test_file.py               # Single file
uv run pytest -k "test_name"                        # Single test by name
```

## Linting & Formatting (from `backend/`)
```bash
uv run ruff check .                                 # Lint
uv run ruff format .                                # Format
uv run ruff check --fix .                           # Auto-fix lint issues
```

## Frontend (from `frontend/`)
```bash
npm install
npm run dev                                         # Vite dev server (port 5173)
npm run build                                       # Production build (tsc + vite)
npm run preview                                     # Preview production build
```

## Util / System (Darwin)
```bash
git log --oneline -10
git status
ls -la
find . -name "*.py" -path "*/apps/*"
grep -r "class_name" backend/apps/
```
