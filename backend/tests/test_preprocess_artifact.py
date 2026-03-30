from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image

from inference_service.core.config import Settings
from inference_service.services.preprocess_artifact import PreprocessArtifactService


def _build_image() -> np.ndarray:
    return np.full((16, 16, 3), 128, dtype=np.uint8)


def test_save_creates_timestamped_task_directory(tmp_path: Path) -> None:
    settings = Settings(
        preprocess_artifact_enabled=True,
        preprocess_artifact_root=str(tmp_path / "artifacts"),
    )
    service = PreprocessArtifactService(
        settings,
        now_provider=lambda: datetime(2026, 3, 30, 14, 25, 30),
    )
    result = service.save("DT202603300001", _build_image(), "source.jpg")
    assert result.saved is True
    assert result.output_dir.endswith("DT202603300001_20260330_142530/preprocessed")
    assert Path(result.output_dir).is_dir()


def test_save_writes_preprocessed_image(tmp_path: Path) -> None:
    settings = Settings(
        preprocess_artifact_enabled=True,
        preprocess_artifact_root=str(tmp_path / "artifacts"),
    )
    service = PreprocessArtifactService(settings)
    result = service.save("DT202603300002", _build_image(), "scene_input.png")
    output_path = Path(result.image_path)
    assert result.saved is True
    assert output_path.name == "scene_input_preprocessed.png"
    assert output_path.exists()
    loaded = np.asarray(Image.open(output_path))
    assert loaded.shape == (16, 16, 3)


def test_save_does_not_create_files_when_disabled(tmp_path: Path) -> None:
    settings = Settings(
        preprocess_artifact_enabled=False,
        preprocess_artifact_root=str(tmp_path / "artifacts"),
    )
    service = PreprocessArtifactService(settings)
    result = service.save("DT202603300003", _build_image(), "source.jpg")
    assert result.enabled is False
    assert result.saved is False
    assert result.output_dir == ""
    assert not (tmp_path / "artifacts").exists()


def test_save_logs_and_does_not_interrupt_when_write_fails(tmp_path: Path, monkeypatch, caplog) -> None:
    settings = Settings(
        preprocess_artifact_enabled=True,
        preprocess_artifact_root=str(tmp_path / "artifacts"),
        preprocess_artifact_fail_on_error=False,
    )
    service = PreprocessArtifactService(settings)

    def raise_save(self, fp, format=None, **params):  # noqa: ANN001, ANN002, ANN003
        raise OSError("disk full")

    monkeypatch.setattr(Image.Image, "save", raise_save)
    with caplog.at_level("WARNING"):
        result = service.save("DT202603300004", _build_image(), "source.jpg")
    assert result.enabled is True
    assert result.saved is False
    assert result.image_path == ""
    assert result.error == "disk full"
    assert "預處理圖像保存失敗" in caplog.text
    assert "DT202603300004" in caplog.text
