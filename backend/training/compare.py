from __future__ import annotations

import argparse
import json
import logging
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import yaml

_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from common.weather_preprocess import prepare_dataset_with_preprocessing
from inference_service.core.config import Settings
from training.config_utils import parse_args_with_config
from training.preprocess_utils import add_preprocess_arguments, build_preprocess_options

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def _inject_yolov13_source_path(settings: Settings) -> None:
    yolov13_root = Path(settings.yolov13_root)
    if yolov13_root.exists() and str(yolov13_root) not in sys.path:
        sys.path.insert(0, str(yolov13_root))


def _load_yolo_class():
    from ultralytics import YOLO
    return YOLO


def _resolve_yaml(data_yaml: Path) -> Path:
    with data_yaml.open(encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    changed = False
    for key in ("path", "train", "val", "test"):
        if key not in cfg:
            continue
        p = Path(str(cfg[key]))
        if not p.is_absolute():
            cfg[key] = str((data_yaml.parent / p).resolve())
            changed = True
    if not changed:
        return data_yaml
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8")
    yaml.dump(cfg, tmp, allow_unicode=True, default_flow_style=False)
    tmp.close()
    return Path(tmp.name)


def _validate_model(model_path: Path, data_yaml: Path, device: str, imgsz: int) -> dict:
    _inject_yolov13_source_path(Settings())
    YOLO = _load_yolo_class()
    model = YOLO(str(model_path))
    results = model.val(data=str(_resolve_yaml(data_yaml)), device=device, imgsz=imgsz, verbose=False)
    def _safe(value) -> float:
        try:
            return round(float(value), 6)
        except Exception:
            return 0.0
    return {
        "model": str(model_path),
        "map50": _safe(results.box.map50),
        "map50_95": _safe(results.box.map),
        "precision": _safe(results.box.mp),
        "recall": _safe(results.box.mr),
    }


def _build_parser(settings: Settings) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="基准模型与预处理实验模型对比评估",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--config", default="", help="YAML/JSON 配置文件路径")
    parser.add_argument("--baseline-model", required=True, help="基准模型路径或 models_root 下的文件名")
    parser.add_argument("--experiment-model", required=True, help="实验模型路径或绝对路径")
    parser.add_argument("--dataset", default="rainfog_detection", help="datasets_root 下的资料集名称")
    parser.add_argument("--device", default="0", help="装置：cpu / 0 / 0,1")
    parser.add_argument("--imgsz", type=int, default=640, help="输入影像大小")
    parser.add_argument("--output-dir", default=str(Path(settings.results_root) / "compare" / datetime.now().strftime("%Y%m%d_%H%M%S")), help="对比报告输出目录")
    add_preprocess_arguments(parser)
    return parser


def _resolve_model(settings: Settings, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return Path(settings.models_root) / value


def _write_markdown(output_path: Path, payload: dict) -> None:
    lines = [
        "# 预处理实验对比报告\n\n",
        f"- 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
        f"- 数据集：`{payload['dataset']}`\n",
        f"- 基准模型权重：`{payload['baseline_model']}`\n",
        f"- 实验模型权重：`{payload['experiment_model']}`\n",
        f"- 预处理模式：`{payload['preprocess']['mode']}`\n",
        f"- 预处理场景：`{payload['preprocess']['profile'] or payload['preprocess']['scene'] or 'auto'}`\n",
        f"- 算法组合：`{', '.join(payload['preprocess']['algorithms']) or 'none'}`\n",
        f"- 派生数据集：`{payload['prepared_dataset']['dataset_root']}`\n\n",
        "## 指标对比\n\n",
        "| 实验 | mAP50 | mAP50-95 | Precision | Recall |\n",
        "|------|------:|---------:|----------:|-------:|\n",
    ]
    for label, metrics in payload["metrics"].items():
        lines.append(
            f"| {label} | {metrics['map50']:.4f} | {metrics['map50_95']:.4f} | {metrics['precision']:.4f} | {metrics['recall']:.4f} |\n"
        )
    output_path.write_text("".join(lines), encoding="utf-8")


def main() -> None:
    settings = Settings()
    parser = _build_parser(settings)
    args, config = parse_args_with_config(parser)
    preprocess_options = build_preprocess_options(args, config)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    baseline_model = _resolve_model(settings, args.baseline_model)
    experiment_model = _resolve_model(settings, args.experiment_model)
    original_yaml = Path(settings.datasets_root) / args.dataset / "data.yaml"
    if not original_yaml.exists():
        raise FileNotFoundError(f"data.yaml 不存在：{original_yaml}")
    metrics = {
        "baseline_no_preprocess": _validate_model(baseline_model, original_yaml, args.device, args.imgsz),
    }
    prepared = prepare_dataset_with_preprocessing(
        settings.datasets_root,
        args.dataset,
        preprocess_options,
        output_root=args.prepared_datasets_root or None,
        overwrite=args.preprocess_overwrite,
    )
    if preprocess_options.is_enabled():
        metrics["baseline_with_preprocess"] = _validate_model(
            baseline_model,
            prepared.data_yaml_path,
            args.device,
            args.imgsz,
        )
        metrics["experiment_with_preprocess"] = _validate_model(
            experiment_model,
            prepared.data_yaml_path,
            args.device,
            args.imgsz,
        )
    else:
        metrics["experiment_no_preprocess"] = _validate_model(experiment_model, original_yaml, args.device, args.imgsz)
    payload = {
        "dataset": args.dataset,
        "baseline_model": str(baseline_model),
        "experiment_model": str(experiment_model),
        "preprocess": preprocess_options.to_dict(),
        "prepared_dataset": prepared.to_dict(),
        "metrics": metrics,
    }
    json_path = output_dir / "compare_report.json"
    md_path = output_dir / "compare_report.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    _write_markdown(md_path, payload)
    logger.info("对比报告已输出：%s", json_path)


if __name__ == "__main__":
    main()
