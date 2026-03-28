"""
資料集 80/20 train/val 分割腳本。

從 dawn-dataset（平鋪結構）隨機分割並複製至 YOLO 標準 train/val 目錄。

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


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="80/20 train/val 分割：dawn-dataset → rainfog_detection/images+labels",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--source",
        default="rainfog_detection/dawn-dataset",
        help="來源子目錄（相對於 datasets_root）",
    )
    parser.add_argument(
        "--target", default="rainfog_detection", help="目標子目錄（相對於 datasets_root）"
    )
    parser.add_argument("--val-ratio", type=float, default=0.2, help="驗證集比例（0~1）")
    parser.add_argument("--seed", type=int, default=42, help="隨機種子（確保可重現）")
    parser.add_argument("--overwrite", action="store_true", help="若目標目錄已有檔案，強制覆蓋")
    return parser


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
) -> int:
    dst_images.mkdir(parents=True, exist_ok=True)
    dst_labels.mkdir(parents=True, exist_ok=True)
    for img, lbl in pairs:
        shutil.copy2(img, dst_images / img.name)
        shutil.copy2(lbl, dst_labels / lbl.name)
    logger.info("  %s：%d 筆 → %s", label, len(pairs), dst_images.parent)
    return len(pairs)


def main() -> None:
    settings = Settings()
    args = _build_parser().parse_args()

    datasets_root = Path(settings.datasets_root)
    src_dir = datasets_root / args.source
    src_images = src_dir / "images"
    src_labels = src_dir / "labels"

    for p in (src_dir, src_images, src_labels):
        if not p.exists():
            logger.error("來源目錄不存在：%s", p)
            sys.exit(1)

    dst_dir = datasets_root / args.target
    dst_train_imgs = dst_dir / "images" / "train"
    dst_val_imgs = dst_dir / "images" / "val"
    dst_train_lbls = dst_dir / "labels" / "train"
    dst_val_lbls = dst_dir / "labels" / "val"

    if not args.overwrite:
        existing = sum(
            1
            for d in (dst_train_imgs, dst_val_imgs)
            if d.exists() and any(f.suffix.lower() in _IMAGE_EXTS for f in d.iterdir())
        )
        if existing:
            logger.error(
                "目標目錄已有圖片，請加 --overwrite 強制覆蓋，或先手動清空：\n  %s\n  %s",
                dst_train_imgs,
                dst_val_imgs,
            )
            sys.exit(1)

    pairs = _collect_pairs(src_images, src_labels)
    if not pairs:
        logger.error("來源目錄找不到任何有效的 (image, label) 配對")
        sys.exit(1)

    random.seed(args.seed)
    random.shuffle(pairs)
    n_val = max(1, int(len(pairs) * args.val_ratio))
    val_pairs = pairs[:n_val]
    train_pairs = pairs[n_val:]

    logger.info("=== 資料集分割 ===")
    logger.info("來源：%s（共 %d 筆）", src_dir, len(pairs))
    logger.info(
        "分割比例：train=%.0f%%  val=%.0f%%  seed=%d",
        (1 - args.val_ratio) * 100,
        args.val_ratio * 100,
        args.seed,
    )

    _copy_split(train_pairs, dst_train_imgs, dst_train_lbls, "train")
    _copy_split(val_pairs, dst_val_imgs, dst_val_lbls, "val")

    logger.info("=== 分割完成 ===")
    logger.info("train：%d 筆 → %s", len(train_pairs), dst_train_imgs)
    logger.info("val  ：%d 筆 → %s", len(val_pairs), dst_val_imgs)


if __name__ == "__main__":
    main()
