from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# 專案根目錄（backend/ 的上一層）
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
# .env 路徑：讀取失敗時 pydantic-settings 靜默跳過，系統環境變數仍可覆蓋
_ENV_FILE = _REPO_ROOT / "backend" / ".env"


class Settings(BaseSettings):
    # ── 應用基本 ──────────────────────────────────────────────
    app_name: str = "RainFog Inference Service"
    app_version: str = "0.1.0"
    # 日誌等級：DEBUG | INFO | WARNING | ERROR
    log_level: str = "INFO"

    # ── 推理模式 ──────────────────────────────────────────────
    # "mock"     ← 回傳固定測試資料，不需模型檔（開發 / CI 環境）
    # "yolov13"  ← 啟用本地真實推理（需完成 Phase 4 環境安裝）
    model_mode: str = "mock"

    # ── YOLOv13 原始碼根目錄 ──────────────────────────────────
    # 需包含 ultralytics/ 子目錄（從 iMoonLab/yolov13 clone）
    # 僅用於 sys.path 注入，不存放模型權重
    yolov13_root: str = str(_REPO_ROOT / "yolov13-main")

    # ── 模型權重 ──────────────────────────────────────────────
    # 放置 .pt 檔的目錄；詳見 data/models/README.md
    models_root: str = str(_REPO_ROOT / "data" / "models")
    # 預設載入的模型規格（可選：yolov13n / s / l / x .pt）
    yolov13_model_file: str = "yolov13n.pt"

    # ── 資料集 ────────────────────────────────────────────────
    # data.yaml 與 images/labels 的上層目錄；詳見 data/datasets/README.md
    datasets_root: str = str(_REPO_ROOT / "data" / "datasets")

    # ── 結果輸出 ──────────────────────────────────────────────
    results_root: str = str(_REPO_ROOT / "data" / "results")
    preprocess_artifact_enabled: bool = True
    preprocess_artifact_root: str = str(_REPO_ROOT / "data" / "results" / "preprocess_artifacts")
    preprocess_artifact_fail_on_error: bool = False

    model_config = SettingsConfigDict(
        env_prefix="INFERENCE_",
        case_sensitive=False,
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",  # 忽略 .env 中非 INFERENCE_ 前綴的欄位（如 DJANGO_*）
    )

    # ── 路徑解析 ──────────────────────────────────────────────

    def get_model_path(self) -> Path:
        """回傳模型權重的絕對路徑。絕對路徑直接使用；相對路徑基於 models_root。"""
        p = Path(self.yolov13_model_file)
        if p.is_absolute():
            return p
        return Path(self.models_root) / self.yolov13_model_file

    def get_results_root(self) -> Path:
        return Path(self.results_root)

    def get_datasets_root(self) -> Path:
        return Path(self.datasets_root)

    def get_preprocess_artifact_root(self) -> Path:
        return Path(self.preprocess_artifact_root)


settings = Settings()
