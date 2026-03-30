"""
資料集 train/val 分割腳本。

從 dawn-dataset（平鋪結構）隨機分割並複製至 YOLO 標準 train/val 目錄。
核心邏輯由 run_split() 提供，可被其他模組直接呼叫（如 train.py --resplit）。

使用方式（在 backend/ 目錄下執行）：
  uv run python -m training.split_dataset [OPTIONS]
"""

from __future__ import annotations

import argparse
import logging
import random
import shutil
import sys
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

_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

_DEFAULT_SOURCE = "dawn-dataset"
_DEFAULT_TARGET = "rainfog_detection"


# ── Public API ─────────────────────────────────────────────────────────────────

def run_split(
    datasets_root: Path | str,
    source: str = _DEFAULT_SOURCE,
    target: str = _DEFAULT_TARGET,
    val_ratio: float = 0.2,
    seed: int | None = None,
) -> dict:
    """
    對 source 目錄做 train/val 隨機分割，輸出至 target 目錄（強制覆蓋既有內容）。

    Args:
        datasets_root: 資料集根目錄（Settings.datasets_root）
        source:        來源子目錄，相對於 datasets_root
        target:        目標子目錄，相對於 datasets_root
        val_ratio:     驗證集比例（0~1）
        seed:          隨機種子；None 或 -1 代表每次隨機，>=0 為固定種子

    Returns:
        dict 包含 {"train": int, "val": int, "seed": int, "source": str}
    """
    datasets_root = Path(datasets_root)
    src_dir    = datasets_root / source
    src_images = src_dir / "images"
    src_labels = src_dir / "labels"

    for p in (src_dir, src_images, src_labels):
        if not p.exists():
            raise FileNotFoundError(f"來源目錄不存在：{p}")

    dst_dir = datasets_root / target
    for split in ("train", "val"):
        (dst_dir / "images" / split).mkdir(parents=True, exist_ok=True)
        (dst_dir / "labels" / split).mkdir(parents=True, exist_ok=True)

    pairs = _collect_pairs(src_images, src_labels)
    if not pairs:
        raise RuntimeError(f"來源目錄找不到任何有效的 (image, label) 配對：{src_dir}")

    actual_seed = seed if (seed is not None and seed >= 0) else None
    random.seed(actual_seed)
    random.shuffle(pairs)
    # 若 actual_seed 為 None，取回實際使用的種子值（以便記錄）
    actual_seed_log = actual_seed if actual_seed is not None else random.randint(0, 2**31)

    n_val = max(1, int(len(pairs) * val_ratio))
    val_pairs   = pairs[:n_val]
    train_pairs = pairs[n_val:]

    logger.info("=== 資料集分割 ===")
    logger.info("來源：%s（共 %d 筆）", src_dir, len(pairs))
    logger.info(
        "分割比例：train=%.0f%%  val=%.0f%%  seed=%s",
        (1 - val_ratio) * 100,
        val_ratio * 100,
        actual_seed if actual_seed is not None else "random",
    )

    _copy_split(train_pairs, dst_dir / "images" / "train", dst_dir / "labels" / "train", "train")
    _copy_split(val_pairs,   dst_dir / "images" / "val",   dst_dir / "labels" / "val",   "val")

    logger.info("=== 分割完成 ===")
    return {"train": len(train_pairs), "val": len(val_pairs), "seed": actual_seed_log, "source": str(src_dir)}


# ── Internals ──────────────────────────────────────────────────────────────────

def _collect_pairs(src_images: Path, src_labels: Path) -> list[tuple[Path, Path]]:
    """收集 (image, label) 配對，跳過找不到對應標注的圖片。"""
    pairs: list[tuple[Path, Path]] = []
    missing = 0
    for img in sorted(src_images.iterdir()):
        if img.suffix.lower() not in _IMAGE_EXTS:
            continue
        lbl = src_labels / (img.stem + ".txt")
        if lbl.exists():
            pairs.append((img, lbl))
        else:
            missing += 1
    if missing:
        logger.warning("跳過 %d 張無對應標注的圖片", missing)
    return pairs


def _copy_split(
    pairs: list[tuple[Path, Path]],
    dst_images: Path,
    dst_labels: Path,
    label: str,
) -> None:
    dst_images.mkdir(parents=True, exist_ok=True)
    dst_labels.mkdir(parents=True, exist_ok=True)
    for img, lbl in pairs:
        shutil.copy2(img, dst_images / img.name)
        shutil.copy2(lbl, dst_labels / lbl.name)
    logger.info("  %s：%d 筆 → %s", label, len(pairs), dst_images.parent)


# ── CLI entry point ────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="train/val 分割：dawn-dataset → rainfog_detection/images+labels",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--source", default=_DEFAULT_SOURCE, help="來源子目錄（相對於 datasets_root）")
    parser.add_argument("--target", default=_DEFAULT_TARGET, help="目標子目錄（相對於 datasets_root）")
    parser.add_argument("--val-ratio", type=float, default=0.2, help="驗證集比例（0~1）")
    parser.add_argument("--seed", type=int, default=-1, help="隨機種子（-1 = 每次不同）")
    parser.add_argument("--overwrite", action="store_true", help="若目標目錄已有檔案，強制覆蓋")
    return parser


def main() -> None:
    settings = Settings()
    args = _build_parser().parse_args()
    datasets_root = Path(settings.datasets_root)

    if not args.overwrite:
        dst_dir = datasets_root / args.target
        has_images = any(
            (dst_dir / "images" / split).exists()
            and any(f.suffix.lower() in _IMAGE_EXTS for f in (dst_dir / "images" / split).iterdir())
            for split in ("train", "val")
            if (dst_dir / "images" / split).exists()
        )
        if has_images:
            logger.error(
                "目標目錄已有圖片，請加 --overwrite 強制覆蓋：%s",
                dst_dir / "images",
            )
            sys.exit(1)

    try:
        result = run_split(
            datasets_root=datasets_root,
            source=args.source,
            target=args.target,
            val_ratio=args.val_ratio,
            seed=args.seed,
        )
        logger.info("train：%d 筆  val：%d 筆  seed=%s", result["train"], result["val"], result["seed"])
    except (FileNotFoundError, RuntimeError) as exc:
        logger.error("%s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
