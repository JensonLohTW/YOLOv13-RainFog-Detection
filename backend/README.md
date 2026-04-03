# Backend Workspace

本目錄使用 `uv` 管理 Python 依賴，包含兩部分：

- Django：業務後台與管理 API
- FastAPI：推理能力服務與 Mock / YOLO 適配器

## 執行基線

- Python：`3.14.x`
- Django：`5.2.x`
- MCP SDK：`1.12+`

若本機尚未安裝 Python 3.14，請先安裝後再執行 `uv sync`。升級主版本後，請重新建立虛擬環境與 lockfile，避免沿用舊的 3.9 / 4.2 解析結果。

## 常用命令

```bash
cd backend
uv python install 3.14
uv venv --python 3.14
uv sync
uv run python manage.py migrate
uv run python manage.py runserver 0.0.0.0:8000
uv run uvicorn inference_service.main:app --reload --host 0.0.0.0 --port 9000
uv run uvicorn mcp_services.inference.app:app --reload --host 0.0.0.0 --port 9100
uv run uvicorn mcp_services.training.app:app --reload --host 0.0.0.0 --port 9101
```

## 結構說明

- `config/`：Django 設定、路由與啟動入口
- `apps/`：領域應用模組
- `common/`：通用工具與 API 返回封裝
- `integrations/inference/`：Django 對 FastAPI 的調用封裝
- `inference_service/`：FastAPI 推理服務
