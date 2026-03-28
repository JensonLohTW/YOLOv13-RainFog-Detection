# Task Completion Checklist

After completing any coding task on this project, run the following:

## Backend changes (Python)
```bash
cd backend
uv run ruff check .          # Must pass with no errors
uv run ruff format .         # Auto-format
uv run pytest                # All tests must pass
```

If models were changed:
```bash
uv run python manage.py makemigrations <app_name>
uv run python manage.py migrate
```

## Frontend changes (TypeScript/React)
```bash
cd frontend
npm run build                # tsc + vite build must succeed (catches type errors)
```

## General
- API responses from Django must use `success_response()` / `error_response()` from `common.api.response`
- New Django apps must register in `config/settings/base.py` `INSTALLED_APPS`
- New URL patterns go in the app's `urls.py` and are included from `config/urls.py`
- FastAPI inference adapter changes: ensure `MockInferenceAdapter` and `YoloV13Adapter` both satisfy the `BaseAdapter` interface in `adapters/base.py`
