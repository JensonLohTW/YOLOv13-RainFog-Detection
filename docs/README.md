# YOLOv13 雨霧天氣系統 - 開發者文檔導覽入口 (Documentation Index)

本目錄 (`/docs`) 包含了整個 YOLOv13 專案的深層技術手冊、架構決策紀錄以及資料科學相關設計。

## 1. 核心文檔索引
- [01-system-design.md](./01-system-design.md) - 系統架構、微服務邊界、資料流與 MySQL E-R 模型設計。
- [02-implementation-roadmap.md](./02-implementation-roadmap.md) - 開發里程碑 (Milestones)、實際工作完成度與後續優化計畫。
- [training-pipeline.md](./training-pipeline.md) - 模型層的資料處理清洗、訓練邏輯與效度指標 (mAP/IoU) 之數學說明。
- [training.md](./training.md) - 具體的模型微調參數與 CLI 指令執行操作手冊。

## 2. 系統快速啟動指南 (Developer Quick Start)

> **環境必備需求**：macOS 或 Linux 環境、Docker 引擎、Python 套件管理器 (`uv`)、Node.js 18+ 環境。

以下指引將協助您在本地端順利起步完整的三微服務叢集：

### 第一步：基礎設施準備與環境變數
```bash
# 生成核心設定檔 (生成後需於文檔填補必要資料與密鑰)
cp backend/.env.example backend/.env

# 於背景啟動 MySQL 資料庫與 Redis 緩存模組
docker compose -f docker-compose.dev.yml up -d
```

### 第二步：啟動業務後端 (Django)
```bash
cd backend
# 透過 uv 安裝核心套件 (若需要直接進行 AI 模型開發可添加 --extra yolo 擴充)
uv sync 

# 第一次執行需建立資料庫表單並宣告初始權限
uv run python manage.py migrate
uv run python manage.py createsuperuser

# 啟動於預設的 8000 端口
uv run python manage.py runserver 0.0.0.0:8000
```

### 第三步：啟動推理服務 (FastAPI)
操作前，請確認 `backend/.env` 中的 `INFERENCE_MODEL_MODE` 變數：
- **`mock`**：純前端串接與業務開發時建議使用的輕型模式 (預設值)。
- **`yolov13`**：正式預測與 AI 測試模式 (前置條件: 確認 `ultralytics` 已安裝且對應的權重模型檔已放置於 `data/models/` 之中)。

```bash
cd backend
# 統一透過 ASGI 啟動於 9000 端口
uv run uvicorn inference_service.main:app --reload --host 0.0.0.0 --port 9000
```

### 第四步：啟動管理前端 (React)
```bash
cd frontend
# 安裝 NPM 依賴模組
npm install

# 啟動 Vite 熱點開發服務，預設於 5173 端口
npm run dev
```

## 3. 自動化測試與工程控管指令
專案內嚴格制定了品質大關，無論提出任何變更修改，必須確保通過下方命令集點驗：

```bash
cd backend
# 執行全部模組之單元/整合測試套件
uv run pytest

# 執行語法強迫靜態檢查與變數分析
uv run ruff check .
```

## 4. 常見故障排除 (Troubleshooting)

1. **問題：在觸發影像分析時報錯 `Connection Refused 9000`。**
   - **檢核點**：代表 FastAPI 服務崩潰或未開啟。請檢查 Terminal 2 的 9000 端口狀況。或檢查 Django 讀取的 `.env` 中的 `INFERENCE_BASE_URL` 網址對否。
2. **問題：React 前端畫面無法登入，網路面板拋出紅字。**
   - **檢核點**：確認 Django (8000 端口) 正常運行，且新開發者是否有記得執行過 `manage.py createsuperuser` 成功申請本機帳戶。
3. **問題：切換至真實模型 `yolov13` 模式，FastAPI 啟動就直接 500 報錯崩潰。**
   - **檢核點**：
      1. `uv` 的依賴包未成功包含 PyTorch，請執行 `uv sync --extra yolo`。
      2. 提示 Weight File Not Found：確認設定的 `INFERENCE_YOLOV13_MODEL_FILE` 名稱相符，且確實位於 `data/models/` 資料夾下。 
