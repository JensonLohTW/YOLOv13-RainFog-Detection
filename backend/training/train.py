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
import json
import logging
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from training.epoch_watcher import EpochWatcher  # noqa: E402

# 確保以 `python -m training.train` 或直接執行時，backend/ 都在 sys.path
_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from common.weather_preprocess import prepare_dataset_with_preprocessing  # noqa: E402
from inference_service.core.config import Settings  # noqa: E402
from training.config_utils import parse_args_with_config  # noqa: E402
from training.preprocess_utils import add_preprocess_arguments, build_preprocess_options  # noqa: E402
from training.split_dataset import run_split  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def _add_file_handler(run_dir: Path, run_name: str) -> Optional[logging.FileHandler]:
    """在 run 目錄建立帶時間戳的 log 檔，每次訓練日誌各自獨立保存。"""
    try:
        run_dir.mkdir(parents=True, exist_ok=True)
        log_file = run_dir / f"{run_name}.log"
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(logging.INFO)
        fh.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logging.getLogger().addHandler(fh)
        logger.info("日誌檔案：%s", log_file)
        return fh
    except Exception as exc:  # noqa: BLE001
        logger.warning("無法建立日誌檔案：%s", exc)
        return None

_REPO_ROOT = _BACKEND_DIR.parent


def _build_parser(settings: Settings) -> argparse.ArgumentParser:
    default_project = str(_REPO_ROOT / "data" / "train_runs")

    parser = argparse.ArgumentParser(
        description="YOLOv13 微調訓練（Fine-Tuning）",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--config", default="", help="YAML/JSON 配置文件路徑")
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
    parser.add_argument("--lr0",    type=float, default=0.01,  help="初始學習率（預設 0.01）")
    parser.add_argument("--lrf",    type=float, default=0.01,  help="最終學習率比例（lr0 * lrf = 最終 lr，預設 0.01）")
    parser.add_argument("--cos-lr", action="store_true",       help="使用 cosine LR 衰減排程（預設 False）")
    # ── 訓練前重新分割資料集 ──────────────────────────────────────────────
    parser.add_argument(
        "--resplit", action="store_true",
        help="訓練開始前自動重新隨機分割 train/val（預設 False）",
    )
    parser.add_argument(
        "--resplit-val-ratio", type=float, default=0.2,
        help="重新分割時的 val 比例（預設 0.2）",
    )
    parser.add_argument(
        "--resplit-seed", type=int, default=-1,
        help="重新分割隨機種子；-1 = 每次不同（真正隨機），>=0 = 固定可重現",
    )
    parser.add_argument(
        "--resplit-source", default="dawn-dataset",
        help="分割來源子目錄，相對於 datasets_root（預設 dawn-dataset）",
    )
    add_preprocess_arguments(parser)
    return parser


def _maybe_resplit(args: argparse.Namespace, settings: Settings) -> dict | None:
    """
    若 --resplit 旗標開啟，在訓練開始前執行一次隨機 train/val 分割。

    Returns:
        分割結果 dict（含 train/val 數量與實際 seed），未啟用時回傳 None。
    """
    if not getattr(args, "resplit", False):
        return None
    logger.info(
        "=== 訓練前重新分割資料集 === val_ratio=%.2f  seed=%s",
        args.resplit_val_ratio,
        args.resplit_seed if args.resplit_seed >= 0 else "random",
    )
    try:
        result = run_split(
            datasets_root=settings.datasets_root,
            source=args.resplit_source,
            target=args.dataset,
            val_ratio=args.resplit_val_ratio,
            seed=args.resplit_seed,
        )
        logger.info(
            "分割完成：train=%d  val=%d  actual_seed=%s",
            result["train"], result["val"], result["seed"],
        )
        return result
    except (FileNotFoundError, RuntimeError) as exc:
        logger.error("資料集分割失敗，訓練中止：%s", exc)
        sys.exit(1)


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


def _run_baseline_eval(model, resolved_yaml: str, run_dir: Path, args: argparse.Namespace) -> None:
    """訓練前對原始預訓練權重執行 val()，基準指標儲存為 baseline_metrics.json。"""
    logger.info("=== 基準評估：對原始 %s 在驗證集執行 val() ===", args.model)
    try:
        val_kwargs: dict = {
            "data": resolved_yaml,
            "imgsz": args.imgsz,
            "verbose": False,
            "save": False,
        }
        if args.device:
            val_kwargs["device"] = args.device

        results = model.val(**val_kwargs)

        def _safe(v) -> float:  # noqa: ANN001
            try:
                return round(float(v), 6)
            except Exception:  # noqa: BLE001
                return 0.0

        baseline = {
            "model": args.model,
            "map50": _safe(results.box.map50),
            "map50_95": _safe(results.box.map),
            "precision": _safe(results.box.mp),
            "recall": _safe(results.box.mr),
        }
        out_path = run_dir / "baseline_metrics.json"
        out_path.write_text(json.dumps(baseline, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info(
            "基準指標已儲存：mAP50=%.4f  mAP50-95=%.4f  P=%.4f  R=%.4f",
            baseline["map50"], baseline["map50_95"], baseline["precision"], baseline["recall"],
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("基準評估失敗（訓練繼續）：%s", exc)


def _write_experiment_manifest(
    run_dir: Path,
    args: argparse.Namespace,
    preprocess_options,
    prepared_dataset,
    model_path: Path,
    resplit_result: dict | None = None,
) -> None:
    manifest = {
        "run_name": args.name,
        "model": str(model_path),
        "dataset": args.dataset,
        "project": args.project,
        "epochs": args.epochs,
        "batch": args.batch,
        "imgsz": args.imgsz,
        "device": args.device or "auto",
        "workers": args.workers,
        "patience": args.patience,
        "resume": args.resume,
        "resplit": {
            "enabled": bool(getattr(args, "resplit", False)),
            "val_ratio": getattr(args, "resplit_val_ratio", 0.2),
            "seed_param": getattr(args, "resplit_seed", -1),
            "source": getattr(args, "resplit_source", ""),
            "result": resplit_result,
        },
        "preprocess": preprocess_options.to_dict(),
        "prepared_dataset": prepared_dataset.to_dict(),
    }
    manifest_path = run_dir / "experiment_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")


def _write_compare_report(save_dir: Path, model, args: argparse.Namespace, preprocess_options, prepared_dataset) -> None:
    baseline_path = save_dir / "baseline_metrics.json"
    if not baseline_path.exists():
        return
    try:
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return
    metrics = {
        "mAP50": _best_metric(model=model, key="metrics/mAP50(B)", default="N/A"),
        "mAP50-95": _best_metric(model=model, key="metrics/mAP50-95(B)", default="N/A"),
        "Precision": _best_metric(model=model, key="metrics/precision(B)", default="N/A"),
        "Recall": _best_metric(model=model, key="metrics/recall(B)", default="N/A"),
    }
    report_lines = [
        "# 基準模型 vs 預處理訓練模型\n\n",
        f"- 基準模型權重：`{args.model}`\n",
        f"- 實驗模型權重：`{save_dir / 'weights' / 'best.pt'}`\n",
        f"- 數據集：`{args.dataset}`\n",
        f"- 預處理模式：`{preprocess_options.normalized_mode()}`\n",
        f"- 預處理場景：`{preprocess_options.normalized_profile() or 'auto'}`\n",
        f"- 算法組合：`{', '.join(preprocess_options.normalized_algorithms()) or 'none'}`\n",
        f"- 派生數據集：`{prepared_dataset.dataset_root}`\n\n",
        "## 指標對比\n\n",
        "| 指標 | 基準模型（無預處理） | 當前訓練最佳 |\n",
        "|------|-------------------:|-------------:|\n",
        f"| mAP50 | {baseline.get('map50', 0.0):.4f} | {metrics['mAP50']} |\n",
        f"| mAP50-95 | {baseline.get('map50_95', 0.0):.4f} | {metrics['mAP50-95']} |\n",
        f"| Precision | {baseline.get('precision', 0.0):.4f} | {metrics['Precision']} |\n",
        f"| Recall | {baseline.get('recall', 0.0):.4f} | {metrics['Recall']} |\n",
    ]
    (save_dir / "experiment_compare.md").write_text("".join(report_lines), encoding="utf-8")


def _get_save_dir(model, project: str, name: str) -> Path:
    try:
        return Path(model.trainer.save_dir)
    except AttributeError:
        return Path(project) / name


def _best_metric(model, key: str, default: str = "N/A") -> str:
    """從 trainer.metrics 或 validator.metrics 取最佳指標，失敗時回傳預設值。"""
    if model is None:
        return default
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
        f"| lr0 | {getattr(args, 'lr0', 0.01)} |\n",
        f"| lrf | {getattr(args, 'lrf', 0.01)} |\n",
        f"| cos_lr | {getattr(args, 'cos_lr', False)} |\n",
        f"| preprocess_mode | {getattr(args, 'preprocess_mode', 'off')} |\n",
        f"| preprocess_profile | {getattr(args, 'preprocess_profile', '') or 'auto'} |\n",
        f"| preprocess_algorithms | {', '.join(getattr(args, 'preprocess_algorithms', [])) or 'auto'} |\n",
        f"| prepared_datasets_root | {getattr(args, 'prepared_datasets_root', '') or 'default'} |\n",
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
        f"| experiment_manifest.json | `{save_dir / 'experiment_manifest.json'}` |\n",
        f"| experiment_compare.md | `{save_dir / 'experiment_compare.md'}` |\n",
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
        ["preprocess_mode", getattr(args, "preprocess_mode", "off")],
        ["preprocess_profile", getattr(args, "preprocess_profile", "") or "auto"],
        ["preprocess_algorithms", ", ".join(getattr(args, "preprocess_algorithms", [])) or "auto"],
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
    args, config = parse_args_with_config(parser)
    preprocess_options = build_preprocess_options(args, config)
    args.preprocess_mode = preprocess_options.normalized_mode()
    args.preprocess_profile = preprocess_options.normalized_profile()
    args.preprocess_algorithms = preprocess_options.normalized_algorithms()

    run_dir = Path(args.project) / args.name
    _add_file_handler(run_dir, args.name)

    logger.info("=== YOLOv13 微調訓練啟動 ===")
    logger.info("模型目錄：%s", settings.models_root)
    logger.info("資料集目錄：%s", settings.datasets_root)
    logger.info("YOLOv13 原始碼：%s", settings.yolov13_root)

    resplit_result = _maybe_resplit(args, settings)

    model_path, data_yaml = _validate_paths(settings, args.model, args.dataset)
    prepared_dataset = prepare_dataset_with_preprocessing(
        settings.datasets_root,
        args.dataset,
        preprocess_options,
        output_root=args.prepared_datasets_root or None,
        overwrite=args.preprocess_overwrite,
    )
    _write_experiment_manifest(run_dir, args, preprocess_options, prepared_dataset, model_path, resplit_result)

    logger.info("--- 訓練參數 ---")
    logger.info("  模型：%s", model_path)
    logger.info("  原始資料集：%s", data_yaml)
    logger.info("  訓練資料集：%s", prepared_dataset.data_yaml_path)
    logger.info("  epochs=%d  batch=%d  imgsz=%d", args.epochs, args.batch, args.imgsz)
    logger.info(
        "  device=%s  workers=%d  patience=%d", args.device or "auto", args.workers, args.patience
    )
    logger.info(
        "  preprocess=%s  profile=%s  algorithms=%s",
        preprocess_options.normalized_mode(),
        preprocess_options.normalized_profile() or "auto",
        ",".join(preprocess_options.normalized_algorithms()) or "auto",
    )
    logger.info("  輸出：%s/%s", args.project, args.name)
    logger.info("  resume=%s", args.resume)
    logger.info(
        "  resplit=%s  val_ratio=%s  seed=%s",
        getattr(args, "resplit", False),
        getattr(args, "resplit_val_ratio", 0.2),
        getattr(args, "resplit_seed", -1) if getattr(args, "resplit_seed", -1) >= 0 else "random",
    )
    logger.info("----------------")

    _inject_yolov13_path(settings)
    YOLO = _load_yolo_class()
    model = YOLO(str(model_path))

    resolved_yaml = _resolve_data_yaml(prepared_dataset.data_yaml_path)
    baseline_yaml = _resolve_data_yaml(data_yaml)
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
        "exist_ok": True,
        "verbose": True,
        "lr0": args.lr0,
        "lrf": args.lrf,
        "cos_lr": args.cos_lr,
    }
    if args.device:
        train_kwargs["device"] = args.device

    logger.info("開始訓練...")

    _run_baseline_eval(model, baseline_yaml, run_dir, args)

    watcher = EpochWatcher(run_dir=run_dir, total_epochs=args.epochs)
    watcher.start()
    try:
        model.train(**train_kwargs)
    finally:
        watcher.stop()

    _print_result_paths(model, args.project, args.name, args)
    _write_compare_report(_get_save_dir(model, args.project, args.name), model, args, preprocess_options, prepared_dataset)


if __name__ == "__main__":
    main()
