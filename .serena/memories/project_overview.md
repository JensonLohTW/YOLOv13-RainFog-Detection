# Project Overview

## Purpose
YOLOv13 RainFog Detection — A full-stack web admin platform for rain/fog weather scene object detection using YOLOv13. Users upload images, submit detection tasks, and view bounding-box results via a React dashboard.

## Tech Stack
- **Backend (Django)**: Python 3.9–3.12, Django 4.2, Django REST Framework 3.15, Token auth, MySQL 8.4, Redis 7.4
- **Inference Service (FastAPI)**: Python, FastAPI 0.115, Uvicorn, Pydantic v2, httpx; switchable adapters (mock / real YOLOv13)
- **Frontend (React)**: Vite + React 18 + TypeScript, shadcn/ui (Radix UI + Tailwind CSS), Zustand, TanStack React Query, React Hook Form + Zod, React Router v6
- **Infrastructure**: Docker Compose (MySQL + Redis), uv (Python package manager), npm

## Implementation Phases
- Phase 0–2: Complete (auth, image upload, task CRUD, mock inference, results, frontend)
- Phase 3: In progress (Redis caching)
- Phase 4: Planned (real YOLOv13 via `ultralytics`, lazy-loaded adapter at `inference_service/adapters/yolov13.py`)
- Phase 5: Planned (Celery async tasks)
