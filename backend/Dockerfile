# 採用 Python 3.10-slim 輕量化底層鏡像，匹配我們要求的程式碼型別語法 (list[str] | None)
FROM python:3.10-slim-bookworm

# 設定工作目錄
WORKDIR /app

# 安裝底層系統依賴，供 OpenCV 與其他底層計算模組執行使用
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 從 Astral 官方來源下載最新版的 `uv` (極速 Python 包管理器)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# 宣告環境變數，強制令 `uv` 行為作用於整個系統 Python (因為我們已處於 Docker 隔離環境中)
ENV UV_SYSTEM_PYTHON=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_TORCH_BACKEND=cpu \
    UV_HTTP_TIMEOUT=300

# 複製 pyproject.toml（不含 uv.lock）以便讓 uv 在 Docker 內重新解析，
# 使 UV_TORCH_BACKEND=cpu 生效，選擇 CPU-only PyTorch (~200MB) 而非 CUDA (~2.5GB)
COPY pyproject.toml ./

# 安裝後端所有依賴套件，--extra yolo 安裝 ultralytics (CPU torch 版本)
RUN uv sync --no-dev --extra yolo

# 將專案代碼的所有內容複製到工作目錄中
COPY . .

# 暴露外部網路溝通的通訊埠 (本專案共用一個 Dockerfile，對應的啟動指令會寫在 docker-compose 內)
EXPOSE 8000 9000

# 預設不設置 CMD，將在拉起時覆蓋
