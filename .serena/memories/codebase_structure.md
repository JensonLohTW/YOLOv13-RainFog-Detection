# Codebase Structure

## Top-Level Layout
```
YOLOv13-RainFog-Detection/
├── backend/               # Python monorepo (Django + FastAPI, managed by uv)
├── frontend/              # React + Vite + TypeScript
├── docs/                  # System design (01-system-design.md) & roadmap (02-implementation-roadmap.md)
├── yolov13-main/          # Original YOLOv13 source (for Phase 4 real inference)
├── data/                  # Uploaded images, result files, model weights (.pt)
├── mysql/                 # MySQL 8.4 local config
├── redis/                 # Redis 7.4 local config
├── scripts/macos/         # Shell scripts: install_all.sh, start_all.sh, docker_up.sh, create_admin.sh
├── scripts/windows/       # PowerShell equivalents
├── logs/                  # Application logs
└── docker-compose.dev.yml # Dev infrastructure (MySQL + Redis only)
```

## Backend Structure (`backend/`)
```
backend/
├── manage.py
├── pyproject.toml          # uv deps, ruff, pytest config
├── config/
│   ├── settings/base.py    # Django core settings
│   ├── settings/dev.py     # Dev overrides (DJANGO_SETTINGS_MODULE=config.settings.dev)
│   ├── urls.py             # Root URL conf (/api/v1/...)
│   ├── wsgi.py / asgi.py
├── apps/
│   ├── accounts/           # Auth: login, token, current user
│   ├── detection/          # DetectionTask, InferenceRecord, DetectionObject models + CRUD
│   ├── media/              # ImageAsset upload/management
│   ├── audit/              # AuditLog
│   ├── dashboard/          # Stats/metrics
│   └── system/             # SystemConfig
├── common/
│   └── api/response.py     # success_response() / error_response()
├── inference_service/      # FastAPI app (separate process, port 9000)
│   ├── main.py             # FastAPI app factory
│   ├── core/config.py      # pydantic-settings config
│   ├── api/routes.py       # /internal/health, /internal/models/current, /internal/inference/detect
│   ├── adapters/           # base.py, mock.py, yolov13.py
│   ├── services/inference.py  # InferencePipeline orchestration
│   └── schemas/            # Pydantic request/response models
├── integrations/
│   └── inference/          # Django-side HTTP client calling FastAPI
└── tests/                  # pytest test suite
```

## Frontend Structure (`frontend/src/`)
```
src/
├── app/App.tsx             # QueryClient provider entry
├── router/index.tsx        # createBrowserRouter; AuthLayout guard
├── pages/                  # login, dashboard, detection, detection-detail, system, audit
├── features/               # Feature-specific business logic components
├── components/
│   └── layout/app-shell.tsx  # Main shell (sidebar + outlet)
├── stores/auth-store.ts    # Zustand: { token, user, setAuth, clearAuth }
├── services/               # API client functions (call Django /api/v1/)
└── lib/                    # Utility functions (cn(), etc.)
```

## Django URL Routes
| Prefix | App |
|--------|-----|
| `/api/v1/auth/` | accounts |
| `/api/v1/detection/` | detection |
| `/api/v1/images/` | media |
| `/api/v1/audit/` | audit |
| `/api/v1/dashboard/` | dashboard |
| `/api/v1/system/` | system |

## Key Data Models
- `DetectionTask` — task_no (DT+timestamp+hex), status (PENDING/QUEUED/PROCESSING/SUCCESS/FAILED/CANCELED), weather_scene (rain/fog/rain_fog/unknown)
- `InferenceRecord` — FK→DetectionTask, engine_type, is_mock, result_image_path, object_count, avg_confidence, duration_ms
- `DetectionObject` — FK→InferenceRecord, class_name, class_id, confidence, bbox_x1/y1/x2/y2
- `ImageAsset` — uploaded image metadata

## Environment Variables (backend/.env)
```
INFERENCE_BASE_URL=http://localhost:9000
INFERENCE_MODEL_MODE=mock          # or "yolov13"
INFERENCE_USE_MOCK=true
INFERENCE_YOLOV13_MODEL_FILE=yolov13n.pt
INFERENCE_MODELS_ROOT=../data/models
INFERENCE_YOLOV13_ROOT=../yolov13-main
```
