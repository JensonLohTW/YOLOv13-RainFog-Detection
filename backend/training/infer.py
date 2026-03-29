from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image

_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from common.weather_preprocess import preprocess_image_file
from inference_service.core.config import Settings
from training.config_utils import parse_args_with_config
from training.preprocess_utils import add_preprocess_arguments, build_preprocess_options

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def _build_parser(settings: Settings) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="YOLOv13 离线推理脚本（支持图像预处理）",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--config", default="", help="YAML/JSON 配置文件路径")
    parser.add_argument("--model", required=True, help="模型路径（绝对路径）或 models_root 下的文件名")
    parser.add_argument("--source", required=True, help="单张图片或图片目录")
    parser.add_argument("--output-dir", default=str(Path(settings.results_root) / "offline_infer" / datetime.now().strftime("%Y%m%d_%H%M%S")), help="输出目录")
    parser.add_argument("--device", default="", help="装置：cpu / 0 / 0,1")
    parser.add_argument("--imgsz", type=int, default=640, help="输入影像大小")
    parser.add_argument("--conf", type=float, default=0.25, help="置信度阈值")
    parser.add_argument("--iou", type=float, default=0.45, help="IoU 阈值")
    add_preprocess_arguments(parser)
    return parser


def _inject_yolov13_path(settings: Settings) -> None:
    root = str(Path(settings.yolov13_root).resolve())
    if root not in sys.path:
        sys.path.insert(0, root)


def _load_yolo_class():
    from ultralytics import YOLO
    return YOLO


def _resolve_model_path(settings: Settings, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return Path(settings.models_root) / value


def _collect_images(source: Path) -> list[Path]:
    if source.is_file():
        return [source]
    return [path for path in sorted(source.rglob("*")) if path.suffix.lower() in _IMAGE_EXTS]


def _save_annotated(result, output_path: Path) -> None:
    annotated_bgr = result.plot()
    annotated_rgb = annotated_bgr[:, :, ::-1]
    Image.fromarray(np.asarray(annotated_rgb, dtype=np.uint8)).save(output_path)


def main() -> None:
    settings = Settings()
    parser = _build_parser(settings)
    args, config = parse_args_with_config(parser)
    preprocess_options = build_preprocess_options(args, config)
    source = Path(args.source)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = _resolve_model_path(settings, args.model)
    if not model_path.exists():
        raise FileNotFoundError(f"模型不存在：{model_path}")
    if not source.exists():
        raise FileNotFoundError(f"推理输入不存在：{source}")
    _inject_yolov13_path(settings)
    YOLO = _load_yolo_class()
    model = YOLO(str(model_path))
    manifest: list[dict] = []
    for image_path in _collect_images(source):
        preprocess_result = preprocess_image_file(image_path, preprocess_options, scene_hint=args.preprocess_scene)
        results = model.predict(
            source=Image.fromarray(preprocess_result.image),
            conf=args.conf,
            iou=args.iou,
            imgsz=args.imgsz,
            verbose=False,
            device=args.device or None,
            save=False,
        )
        result = results[0]
        out_name = image_path.stem + "_result.jpg"
        output_path = output_dir / out_name
        _save_annotated(result, output_path)
        objects = []
        if result.boxes is not None:
            for box in result.boxes:
                x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
                objects.append(
                    {
                        "class_id": int(box.cls[0]),
                        "class_name": result.names.get(int(box.cls[0]), str(int(box.cls[0]))),
                        "confidence": round(float(box.conf[0]), 4),
                        "bbox": [x1, y1, x2, y2],
                    }
                )
        manifest.append(
            {
                "image": str(image_path),
                "output_image": str(output_path),
                "preprocess": preprocess_result.metadata(),
                "object_count": len(objects),
                "objects": objects,
            }
        )
    manifest_path = output_dir / "inference_manifest.json"
    manifest_path.write_text(json.dumps({
        "model": str(model_path),
        "source": str(source),
        "preprocess": preprocess_options.to_dict(),
        "items": manifest,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("离线推理完成：%s", manifest_path)


if __name__ == "__main__":
    main()
