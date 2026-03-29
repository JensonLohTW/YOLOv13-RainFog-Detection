# 採用 Python 3.10-slim 輕量化底層鏡像，匹配我們要求的程式碼型別語法 (list[str] | None)
FROM python:3.10-slim

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
    PYTHONDONTWRITEBYTECODE=1

# 首要複製專案之 package 描述檔與 lock 檔以便利用 docker cache 分層緩存
COPY pyproject.toml uv.lock ./

# 安裝後端所有依賴套件套件，其中 --extra yolo 代表我們預設支援真實推論環境
RUN uv sync --frozen --no-dev --extra yolo

# 將專案代碼的所有內容複製到工作目錄中
COPY . .

# 暴露外部網路溝通的通訊埠 (本專案共用一個 Dockerfile，對應的啟動指令會寫在 docker-compose 內)
EXPOSE 8000 9000

# 預設不設置 CMD，將在拉起時覆蓋
