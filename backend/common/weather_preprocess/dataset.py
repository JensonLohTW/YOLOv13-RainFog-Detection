from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path

from common.weather_preprocess.pipeline import PREPROCESS_MODE_OFF, PreprocessOptions, preprocess_image_file

_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


@dataclass
class PreparedDataset:
    source_dataset_name: str
    dataset_root: Path
    data_yaml_path: Path
    manifest_path: Path | None
    generated: bool
    preprocess: dict
    splits: dict
    scene_counts: dict

    def to_dict(self) -> dict:
        data = asdict(self)
        data["dataset_root"] = str(self.dataset_root)
        data["data_yaml_path"] = str(self.data_yaml_path)
        data["manifest_path"] = str(self.manifest_path) if self.manifest_path else ""
        return data


def _rewrite_data_yaml(source_yaml: Path, target_yaml: Path, dataset_root: Path) -> None:
    lines = source_yaml.read_text(encoding="utf-8").splitlines(keepends=True)
    output: list[str] = []
    replaced = False
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("path:"):
            output.append(f"path: {dataset_root.resolve()}\n")
            replaced = True
        else:
            output.append(line)
    if not replaced:
        output.insert(0, f"path: {dataset_root.resolve()}\n")
    target_yaml.write_text("".join(output), encoding="utf-8")


def _iter_split_images(split_dir: Path):
    if not split_dir.exists():
        return []
    return [path for path in sorted(split_dir.rglob("*")) if path.suffix.lower() in _IMAGE_EXTS]


def prepare_dataset_with_preprocessing(
    datasets_root: str | Path,
    dataset_name: str,
    options: PreprocessOptions | dict | None,
    *,
    output_root: str | Path | None = None,
    overwrite: bool = False,
) -> PreparedDataset:
    preprocess_options = options if isinstance(options, PreprocessOptions) else PreprocessOptions.from_mapping(options)
    source_root = Path(datasets_root) / dataset_name
    source_yaml = source_root / "data.yaml"
    if preprocess_options.normalized_mode() == PREPROCESS_MODE_OFF:
        return PreparedDataset(
            source_dataset_name=dataset_name,
            dataset_root=source_root,
            data_yaml_path=source_yaml,
            manifest_path=None,
            generated=False,
            preprocess=preprocess_options.to_dict(),
            splits={},
            scene_counts={},
        )
    prepared_root_base = Path(output_root) if output_root else Path(datasets_root) / "_prepared"
    prepared_name = f"{dataset_name}__{preprocess_options.signature()}"
    prepared_root = prepared_root_base / prepared_name
    manifest_path = prepared_root / "preprocess_manifest.json"
    if overwrite and prepared_root.exists():
        shutil.rmtree(prepared_root)
    if manifest_path.exists() and not overwrite:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        return PreparedDataset(
            source_dataset_name=dataset_name,
            dataset_root=prepared_root,
            data_yaml_path=prepared_root / "data.yaml",
            manifest_path=manifest_path,
            generated=True,
            preprocess=preprocess_options.to_dict(),
            splits=dict(manifest.get("splits", {})),
            scene_counts=dict(manifest.get("scene_counts", {})),
        )
    prepared_root.mkdir(parents=True, exist_ok=True)
    split_counts: dict[str, int] = {}
    scene_counts: dict[str, int] = {}
    for split in ("train", "val", "test"):
        src_images = source_root / "images" / split
        src_labels = source_root / "labels" / split
        if not src_images.exists() or not src_labels.exists():
            continue
        dst_images = prepared_root / "images" / split
        dst_labels = prepared_root / "labels" / split
        dst_images.mkdir(parents=True, exist_ok=True)
        dst_labels.mkdir(parents=True, exist_ok=True)
        count = 0
        for image_path in _iter_split_images(src_images):
            rel_path = image_path.relative_to(src_images)
            label_path = src_labels / rel_path.with_suffix(".txt")
            out_image = dst_images / rel_path
            out_label = dst_labels / rel_path.with_suffix(".txt")
            out_image.parent.mkdir(parents=True, exist_ok=True)
            out_label.parent.mkdir(parents=True, exist_ok=True)
            result = preprocess_image_file(image_path, preprocess_options, output_path=out_image)
            if label_path.exists():
                shutil.copy2(label_path, out_label)
            scene_counts[result.scene] = scene_counts.get(result.scene, 0) + 1
            count += 1
        split_counts[split] = count
    classes_file = source_root / "classes.txt"
    if classes_file.exists():
        shutil.copy2(classes_file, prepared_root / "classes.txt")
    _rewrite_data_yaml(source_yaml, prepared_root / "data.yaml", prepared_root)
    manifest = {
        "source_dataset_name": dataset_name,
        "source_dataset_root": str(source_root),
        "prepared_dataset_root": str(prepared_root),
        "preprocess": preprocess_options.to_dict(),
        "splits": split_counts,
        "scene_counts": scene_counts,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return PreparedDataset(
        source_dataset_name=dataset_name,
        dataset_root=prepared_root,
        data_yaml_path=prepared_root / "data.yaml",
        manifest_path=manifest_path,
        generated=True,
        preprocess=preprocess_options.to_dict(),
        splits=split_counts,
        scene_counts=scene_counts,
    )
