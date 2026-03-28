"""
YOLOv13 微調訓練腳本（Fine-Tuning）。

使用方式（在 backend/ 目錄下執行）：
  uv run python -m training.train [OPTIONS]

前置條件：
  1. uv sync --extra yolo
  2. data/datasets/rainfog_detection/（準備好 images/ 與 labels/）
  3. data/models/yolov13n.pt（預訓練權重已存在）

詳細說明見 docs/training.md。
"""

from __future__ import annotations

import argparse
import csv
import logging
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# 確保以 `python -m training.train` 或直接執行時，backend/ 都在 sys.path
_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from inference_service.core.config import Settings  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

_REPO_ROOT = _BACKEND_DIR.parent


def _build_parser(settings: Settings) -> argparse.ArgumentParser:
    default_project = str(_REPO_ROOT / "data" / "train_runs")

    parser = argparse.ArgumentParser(
        description="YOLOv13 微調訓練（Fine-Tuning）",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--model",
        default=settings.yolov13_model_file,
        help="模型規格檔名（yolov13n / s / l / x .pt），從 models_root 載入",
    )
    parser.add_argument(
        "--dataset",
        default="rainfog_detection",
        help="datasets_root 下的資料集子目錄名稱",
    )
    parser.add_argument("--epochs", type=int, default=50, help="訓練 epoch 數")
    parser.add_argument("--batch", type=int, default=16, help="批次大小（-1 = 自動）")
    parser.add_argument("--imgsz", type=int, default=640, help="輸入影像大小（像素）")
    parser.add_argument("--device", default="", help="訓練裝置：cpu / 0 / 0,1（空字串 = 自動）")
    parser.add_argument("--workers", type=int, default=4, help="DataLoader 工作執行緒數")
    parser.add_argument(
        "--patience", type=int, default=20, help="Early stopping：無改善的最大 epoch 數"
    )
    parser.add_argument("--project", default=default_project, help="輸出根目錄")
    default_name = "rainfog_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    parser.add_argument("--name", default=default_name, help="訓練執行名稱（區分不同實驗）")
    parser.add_argument("--resume", action="store_true", help="從上次中斷處繼續訓練")
    return parser


def _validate_paths(settings: Settings, model_file: str, dataset_name: str) -> tuple[Path, Path]:
    """校驗模型權重與 data.yaml 是否存在；缺失時輸出明確錯誤並 exit(1)。"""
    model_path = Path(settings.models_root) / model_file
    if not model_path.exists():
        logger.error(
            "預訓練權重不存在：%s\n"
            "  請確認檔案已放至：%s\n"
            "  可用規格：yolov13n.pt / yolov13s.pt / yolov13l.pt / yolov13x.pt\n"
            "  下載：https://github.com/iMoonLab/yolov13/releases",
            model_path,
            settings.models_root,
        )
        sys.exit(1)

    data_yaml = Path(settings.datasets_root) / dataset_name / "data.yaml"
    if not data_yaml.exists():
        logger.error(
            "資料集設定檔不存在：%s\n"
            "  預期目錄結構：\n"
            "    %s/\n"
            "      images/train/  images/val/\n"
            "      labels/train/  labels/val/\n"
            "      data.yaml（nc、names、train/val 路徑）",
            data_yaml,
            Path(settings.datasets_root) / dataset_name,
        )
        sys.exit(1)

    return model_path, data_yaml


def _resolve_data_yaml(data_yaml: Path) -> str:
    """
    將 data.yaml 中 path 欄位置換為絕對路徑，寫入暫存檔後回傳路徑字串。
    ultralytics 在解析 path: . 時會以 settings.datasets_dir（~/datasets）為基底，
    導致路徑解析錯誤；注入絕對路徑可完全規避此問題。
    """
    dataset_root = str(data_yaml.parent.resolve())
    lines = data_yaml.read_text(encoding="utf-8").splitlines(keepends=True)
    new_lines = []
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("path:"):
            new_lines.append(f"path: {dataset_root}\n")
        else:
            new_lines.append(line)
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8")
    tmp.writelines(new_lines)
    tmp.flush()
    tmp.close()
    logger.debug("暫存 data.yaml（絕對路徑）：%s", tmp.name)
    return tmp.name


def _inject_yolov13_path(settings: Settings) -> None:
    """將 yolov13-main 加入 sys.path，優先使用本地 ultralytics 版本。"""
    yolov13_root = str(Path(settings.yolov13_root).resolve())
    if yolov13_root not in sys.path:
        sys.path.insert(0, yolov13_root)


def _load_yolo_class():
    try:
        from ultralytics import YOLO  # noqa: PLC0415

        return YOLO
    except ImportError as exc:
        raise RuntimeError(
            "ultralytics 未安裝，無法進行訓練。\n"
            "  Apple Silicon / Linux / Windows：cd backend && uv sync --extra yolo\n"
            "  Intel Mac（x86_64）：\n"
            "    conda install pytorch torchvision cpuonly -c pytorch\n"
            "    pip install ultralytics"
        ) from exc


def _get_save_dir(model, project: str, name: str) -> Path:
    try:
        return Path(model.trainer.save_dir)
    except AttributeError:
        return Path(project) / name


def _best_metric(model, key: str, default: str = "N/A") -> str:
    """從 trainer.metrics 或 validator.metrics 取最佳指標，失敗時回傳預設值。"""
    try:
        val = model.trainer.metrics.get(key)
        return f"{val:.4f}" if val is not None else default
    except AttributeError:
        return default


def _write_summary(model, args: argparse.Namespace, save_dir: Path) -> None:
    """訓練完成後產生 training_summary.md 與 training_summary.csv。"""
    best_pt = save_dir / "weights" / "best.pt"
    last_pt = save_dir / "weights" / "last.pt"

    map50 = _best_metric(model, "metrics/mAP50(B)")
    map50_95 = _best_metric(model, "metrics/mAP50-95(B)")
    precision = _best_metric(model, "metrics/precision(B)")
    recall = _best_metric(model, "metrics/recall(B)")

    md_lines = [
        "# 訓練摘要\n",
        f"**執行名稱**：{args.name}\n",
        f"**完成時間**：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
        "\n## 訓練參數\n",
        "| 參數 | 值 |\n|------|-----|\n",
        f"| model | {args.model} |\n",
        f"| epochs | {args.epochs} |\n",
        f"| batch | {args.batch} |\n",
        f"| imgsz | {args.imgsz} |\n",
        f"| device | {args.device or 'auto'} |\n",
        f"| workers | {args.workers} |\n",
        f"| patience | {args.patience} |\n",
        "\n## 最佳指標\n",
        "| 指標 | 值 |\n|------|-----|\n",
        f"| mAP50 | {map50} |\n",
        f"| mAP50-95 | {map50_95} |\n",
        f"| Precision | {precision} |\n",
        f"| Recall | {recall} |\n",
        "\n## 產物路徑\n",
        "| 檔案 | 路徑 |\n|------|-----|\n",
        f"| best.pt | `{best_pt}` |\n",
        f"| last.pt | `{last_pt}` |\n",
        f"| results.csv | `{save_dir / 'results.csv'}` |\n",
        f"| results.png | `{save_dir / 'results.png'}` |\n",
        f"| confusion_matrix.png | `{save_dir / 'confusion_matrix.png'}` |\n",
    ]
    md_path = save_dir / "training_summary.md"
    md_path.write_text("".join(md_lines), encoding="utf-8")

    csv_path = save_dir / "training_summary.csv"
    rows = [
        ["name", args.name],
        ["model", args.model],
        ["epochs", args.epochs],
        ["batch", args.batch],
        ["imgsz", args.imgsz],
        ["device", args.device or "auto"],
        ["mAP50", map50],
        ["mAP50-95", map50_95],
        ["Precision", precision],
        ["Recall", recall],
        ["best_pt", str(best_pt)],
        ["last_pt", str(last_pt)],
        ["save_dir", str(save_dir)],
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)

    logger.info("訓練摘要：%s", md_path)
    logger.info("CSV 摘要：%s", csv_path)


def _print_result_paths(model, project: str, name: str, args: argparse.Namespace) -> None:
    """訓練結束後輸出 best.pt / last.pt 路徑，並寫入摘要檔案。"""
    save_dir = _get_save_dir(model, project, name)
    best_pt = save_dir / "weights" / "best.pt"
    last_pt = save_dir / "weights" / "last.pt"

    logger.info("=== 訓練完成 ===")
    logger.info("結果目錄：%s", save_dir)
    logger.info(
        "最佳權重：%s%s",
        best_pt,
        "" if best_pt.exists() else "（尚未生成，請確認訓練是否正常結束）",
    )
    logger.info(
        "最後權重：%s%s",
        last_pt,
        "" if last_pt.exists() else "（尚未生成）",
    )

    _write_summary(model, args, save_dir)


def main() -> None:
    settings = Settings()
    parser = _build_parser(settings)
    args = parser.parse_args()

    logger.info("=== YOLOv13 微調訓練啟動 ===")
    logger.info("模型目錄：%s", settings.models_root)
    logger.info("資料集目錄：%s", settings.datasets_root)
    logger.info("YOLOv13 原始碼：%s", settings.yolov13_root)

    model_path, data_yaml = _validate_paths(settings, args.model, args.dataset)

    logger.info("--- 訓練參數 ---")
    logger.info("  模型：%s", model_path)
    logger.info("  資料集：%s", data_yaml)
    logger.info("  epochs=%d  batch=%d  imgsz=%d", args.epochs, args.batch, args.imgsz)
    logger.info(
        "  device=%s  workers=%d  patience=%d", args.device or "auto", args.workers, args.patience
    )
    logger.info("  輸出：%s/%s", args.project, args.name)
    logger.info("  resume=%s", args.resume)
    logger.info("----------------")

    _inject_yolov13_path(settings)
    YOLO = _load_yolo_class()
    model = YOLO(str(model_path))

    resolved_yaml = _resolve_data_yaml(data_yaml)
    train_kwargs: dict = {
        "data": resolved_yaml,
        "epochs": args.epochs,
        "batch": args.batch,
        "imgsz": args.imgsz,
        "workers": args.workers,
        "project": args.project,
        "name": args.name,
        "patience": args.patience,
        "resume": args.resume,
        "verbose": True,
    }
    if args.device:
        train_kwargs["device"] = args.device

    logger.info("開始訓練...")
    model.train(**train_kwargs)

    _print_result_paths(model, args.project, args.name, args)


if __name__ == "__main__":
    main()
