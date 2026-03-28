# Code Style & Conventions

## Python (Backend)
- **Formatter/Linter**: ruff, line-length=100, target-version=py39
- **Type hints**: Used selectively (Pydantic models are fully typed; Django views use `# noqa: ANN001` to suppress missing type annotations on `request`)
- **Docstrings**: Not used; inline comments in Traditional Chinese for complex logic
- **Naming**: snake_case for functions/variables, PascalCase for classes
- **Django Models**: Always define `db_table` in `Meta`; use `TextChoices` nested inner classes for enum fields; explicit `ordering` and `indexes` in `Meta`
- **API responses**: Always use `success_response()` / `error_response()` from `common.api.response` (returns `{code, message, data}` envelope)
- **Django views**: Class-based (`APIView`), currently `authentication_classes = []` and `permission_classes = []` (auth enforcement planned for later phases)
- **Services pattern**: Business logic lives in `services.py` per app; views delegate to service classes (e.g., `DetectionTaskService`)
- **Imports**: Standard → third-party → local, separated by blank lines

## FastAPI (Inference Service)
- **Schemas**: Pydantic v2 models in `inference_service/schemas/`
- **Adapters**: Abstract base `base.py`, `mock.py` (default), `yolov13.py` (Phase 4); selected via env var `INFERENCE_MODEL_MODE`
- **Config**: `pydantic-settings` in `inference_service/core/config.py`

## TypeScript / React (Frontend)
- **No explicit lint config** (no eslint config visible); TypeScript strict mode via `tsconfig.json`
- **Naming**: PascalCase for components/pages, kebab-case for file names (e.g., `detection-page.tsx`)
- **Imports**: `@/` alias maps to `src/`
- **State**: Zustand for global auth state; React Query for server state
- **Forms**: React Hook Form + Zod schemas for validation
- **UI**: shadcn/ui components (Radix UI primitives + Tailwind)
- **Routes**: Protected by `AuthLayout` — checks Zustand token; redirects to `/login` if absent

## Comment Language
Comments are written in **Traditional Chinese** (繁體中文).
