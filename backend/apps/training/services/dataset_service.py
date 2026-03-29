"""資料集服務：處理 ZIP 上傳、解壓、驗證、train/val 分割。"""
from __future__ import annotations

import logging
import random
import shutil
import zipfile
from pathlib import Path

from django.conf import settings

from apps.training.models import TrainingDataset

logger = logging.getLogger(__name__)

_DATASETS_ROOT = Path(settings.REPO_ROOT) / "data" / "datasets"
_SUPPORTED_IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


class DatasetValidationError(Exception):
    pass


class DatasetService:
    def upload_and_prepare(
        self,
        zip_file,
        name: str,
        description: str = "",
        val_ratio: float = 0.2,
        seed: int = 42,
    ) -> TrainingDataset:
        record = TrainingDataset.objects.create(
            name=name,
            description=description,
            zip_original_name=getattr(zip_file, "name", ""),
            status=TrainingDataset.Status.UPLOADING,
        )
        try:
            dataset_path = self._extract_and_split(zip_file, name, val_ratio, seed, record)
            record.dataset_path = str(dataset_path)
            record.status = TrainingDataset.Status.READY
            record.save(update_fields=["dataset_path", "status", "num_train", "num_val", "num_classes", "_class_names", "updated_at"])
        except Exception as exc:  # noqa: BLE001
            logger.exception("資料集處理失敗：%s", exc)
            record.status = TrainingDataset.Status.FAILED
            record.error_message = str(exc)
            record.save(update_fields=["status", "error_message", "updated_at"])
            raise
        return record

    def _extract_and_split(
        self,
        zip_file,
        name: str,
        val_ratio: float,
        seed: int,
        record: TrainingDataset,
    ) -> Path:
        extract_tmp = _DATASETS_ROOT / f"_tmp_{name}"
        target = _DATASETS_ROOT / name
        if target.exists():
            shutil.rmtree(target)
        extract_tmp.mkdir(parents=True, exist_ok=True)
        try:
            with zipfile.ZipFile(zip_file, "r") as zf:
                zf.extractall(extract_tmp)

            src_root = self._find_dataset_root(extract_tmp)
            self._validate_structure(src_root)

            classes = self._read_classes(src_root)
            pairs = self._collect_pairs(src_root)
            if not pairs:
                raise DatasetValidationError("ZIP 內未找到任何有效的 image/label 配對。")

            rng = random.Random(seed)
            rng.shuffle(pairs)
            split_idx = max(1, int(len(pairs) * (1 - val_ratio)))
            train_pairs = pairs[:split_idx]
            val_pairs = pairs[split_idx:]

            for split, split_pairs in [("train", train_pairs), ("val", val_pairs)]:
                (target / "images" / split).mkdir(parents=True, exist_ok=True)
                (target / "labels" / split).mkdir(parents=True, exist_ok=True)
                for img_path, lbl_path in split_pairs:
                    shutil.copy2(img_path, target / "images" / split / img_path.name)
                    shutil.copy2(lbl_path, target / "labels" / split / lbl_path.name)

            self._write_data_yaml(target, classes)

            record.num_train = len(train_pairs)
            record.num_val = len(val_pairs)
            record.num_classes = len(classes)
            record.class_names = classes
        finally:
            shutil.rmtree(extract_tmp, ignore_errors=True)

        return target

    def _find_dataset_root(self, extract_dir: Path) -> Path:
        """支援 ZIP 根目錄或單層子目錄打包兩種形式。"""
        if (extract_dir / "images").exists() or (extract_dir / "classes.txt").exists():
            return extract_dir
        children = [c for c in extract_dir.iterdir() if c.is_dir()]
        if len(children) == 1:
            candidate = children[0]
            if (candidate / "images").exists() or (candidate / "classes.txt").exists():
                return candidate
        return extract_dir

    def _validate_structure(self, src: Path) -> None:
        if not (src / "images").exists():
            raise DatasetValidationError("ZIP 缺少 images/ 目錄。")
        if not (src / "labels").exists():
            raise DatasetValidationError("ZIP 缺少 labels/ 目錄。")
        if not (src / "classes.txt").exists():
            raise DatasetValidationError("ZIP 缺少 classes.txt 文件。")

    def _read_classes(self, src: Path) -> list[str]:
        lines = (src / "classes.txt").read_text(encoding="utf-8").splitlines()
        classes = [l.strip() for l in lines if l.strip()]
        if not classes:
            raise DatasetValidationError("classes.txt 為空。")
        return classes

    def _collect_pairs(self, src: Path) -> list[tuple[Path, Path]]:
        images_dir = src / "images"
        labels_dir = src / "labels"
        pairs: list[tuple[Path, Path]] = []
        for img in sorted(images_dir.rglob("*")):
            if img.suffix.lower() not in _SUPPORTED_IMG_EXTS:
                continue
            lbl = labels_dir / img.relative_to(images_dir).with_suffix(".txt")
            if lbl.exists():
                pairs.append((img, lbl))
        return pairs

    def _write_data_yaml(self, target: Path, classes: list[str]) -> None:
        names_str = "\n".join(f"  {i}: {c}" for i, c in enumerate(classes))
        yaml_content = (
            f"path: {target}\n"
            f"train: images/train\n"
            f"val: images/val\n"
            f"nc: {len(classes)}\n"
            f"names:\n{names_str}\n"
        )
        (target / "data.yaml").write_text(yaml_content, encoding="utf-8")
