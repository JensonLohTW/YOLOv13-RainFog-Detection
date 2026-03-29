"""
模型驗證腳本：在指定資料集上執行 model.val() 並輸出 JSON 指標。

使用方式（在 backend/ 目錄下執行）：
  uv run python -m training.validate --model yolov13l.pt --dataset rainfog_detection --output /path/to/out.json
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import tempfile
from pathlib import Path

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


def _inject_yolov13_source_path(settings: Settings) -> None:
    yolov13_root = Path(settings.yolov13_root)
    if yolov13_root.exists() and str(yolov13_root) not in sys.path:
        sys.path.insert(0, str(yolov13_root))


def _load_yolo_class():
    try:
        from ultralytics import YOLO
        return YOLO
    except ImportError:
        logger.error("ultralytics 未安裝，請執行：uv sync --extra yolo")
        sys.exit(1)


def _resolve_data_yaml(data_yaml: Path) -> Path:
    import yaml

    with data_yaml.open(encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    changed = False
    for key in ("path", "train", "val", "test"):
        if key not in cfg:
            continue
        p = Path(str(cfg[key]))
        if not p.is_absolute():
            resolved = (data_yaml.parent / p).resolve()
            cfg[key] = str(resolved)
            changed = True

    if not changed:
        return data_yaml

    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    )
    yaml.dump(cfg, tmp, allow_unicode=True, default_flow_style=False)
    tmp.close()
    return Path(tmp.name)


def main() -> None:
    settings = Settings()
    parser = argparse.ArgumentParser(
        description="在指定資料集上執行 YOLOv13 模型驗證，輸出 JSON 指標",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--model", required=True, help="模型路徑（絕對路徑）或 models_root 下的檔名")
    parser.add_argument("--dataset", required=True, help="datasets_root 下的資料集子目錄名稱")
    parser.add_argument("--output", required=True, help="輸出 JSON 檔案路徑")
    parser.add_argument("--device", default="0", help="裝置：cpu / 0 / 0,1")
    parser.add_argument("--imgsz", type=int, default=640, help="輸入影像大小")
    args = parser.parse_args()

    model_path = Path(args.model)
    if not model_path.is_absolute():
        model_path = Path(settings.models_root) / args.model
    if not model_path.exists():
        logger.error("模型檔案不存在：%s", model_path)
        sys.exit(1)

    data_yaml = Path(settings.datasets_root) / args.dataset / "data.yaml"
    if not data_yaml.exists():
        logger.error("data.yaml 不存在：%s", data_yaml)
        sys.exit(1)

    resolved_yaml = _resolve_data_yaml(data_yaml)
    _inject_yolov13_source_path(settings)
    YOLO = _load_yolo_class()

    logger.info("載入模型：%s", model_path)
    model = YOLO(str(model_path))

    logger.info("開始驗證（dataset=%s, device=%s）…", args.dataset, args.device)
    results = model.val(
        data=str(resolved_yaml),
        device=args.device,
        imgsz=args.imgsz,
        verbose=False,
    )

    def _safe(v) -> float:  # noqa: ANN001
        try:
            return round(float(v), 6)
        except Exception:  # noqa: BLE001
            return 0.0

    output = {
        "model": str(model_path),
        "dataset": args.dataset,
        "map50": _safe(results.box.map50),
        "map50_95": _safe(results.box.map),
        "precision": _safe(results.box.mp),
        "recall": _safe(results.box.mr),
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("驗證完成，結果已寫入：%s", out_path)
    logger.info("mAP50=%.4f  mAP50-95=%.4f  P=%.4f  R=%.4f",
                output["map50"], output["map50_95"], output["precision"], output["recall"])


if __name__ == "__main__":
    main()
