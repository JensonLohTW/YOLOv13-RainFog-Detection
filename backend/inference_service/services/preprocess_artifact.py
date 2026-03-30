from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image

from inference_service.core.config import Settings


@dataclass(frozen=True)
class PreprocessArtifactResult:
    enabled: bool
    saved: bool
    output_dir: str
    image_path: str
    error: str = ""

    def metadata(self) -> dict[str, str | bool]:
        return {
            "enabled": self.enabled,
            "saved": self.saved,
            "output_dir": self.output_dir,
            "image_path": self.image_path,
            "error": self.error,
        }


class PreprocessArtifactService:
    def __init__(
        self,
        settings: Settings,
        now_provider: Callable[[], datetime] | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.settings = settings
        self.now_provider = now_provider or datetime.now
        self.logger = logger or logging.getLogger(__name__)

    def save(self, task_id: str, image: np.ndarray, original_image_path: str) -> PreprocessArtifactResult:
        if not self.settings.preprocess_artifact_enabled:
            return PreprocessArtifactResult(False, False, "", "")
        timestamp = self.now_provider().strftime("%Y%m%d_%H%M%S")
        output_dir = self._build_output_dir(task_id, timestamp)
        output_path = self._build_output_path(output_dir, original_image_path)
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            Image.fromarray(np.asarray(image, dtype=np.uint8), mode="RGB").save(output_path)
            return PreprocessArtifactResult(True, True, str(output_dir), str(output_path))
        except Exception as exc:  # noqa: BLE001
            self.logger.warning(
                "預處理圖像保存失敗，task_id=%s，output_dir=%s，output_path=%s，error=%s",
                task_id,
                output_dir,
                output_path,
                exc,
            )
            if self.settings.preprocess_artifact_fail_on_error:
                raise
            return PreprocessArtifactResult(True, False, str(output_dir), "", str(exc))

    def _build_output_dir(self, task_id: str, timestamp: str) -> Path:
        safe_task_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(task_id).strip()) or "task"
        return self.settings.get_preprocess_artifact_root() / f"{safe_task_id}_{timestamp}" / "preprocessed"

    def _build_output_path(self, output_dir: Path, original_image_path: str) -> Path:
        source = Path(original_image_path)
        stem = source.stem or "image"
        suffix = source.suffix or ".png"
        return output_dir / f"{stem}_preprocessed{suffix}"
