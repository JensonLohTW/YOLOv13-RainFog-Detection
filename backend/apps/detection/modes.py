from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.conf import settings

SUPPORTED_RECOGNITION_MODES = {"scene_default", "image"}
SUPPORTED_WEATHER_SCENES = {"rain", "fog", "rain_fog", "unknown"}


@dataclass(frozen=True)
class ResolvedDetectionConfig:
    recognition_mode: str
    weather_scene: str
    confidence_threshold: float
    iou_threshold: float
    preprocess_mode: str
    preprocess_profile: str
    preprocess_algorithms: list[str]
    preprocess_algorithm_params: dict[str, Any]
    preprocess_enable_gamma: bool
    runtime_options: dict[str, Any]


class RecognitionModeResolver:
    def resolve(
        self,
        recognition_mode: str | None,
        weather_scene: str | None,
        confidence_threshold: float | None,
        iou_threshold: float | None,
        preprocess_mode: str | None,
        preprocess_profile: str | None,
        preprocess_algorithms: list[str] | None,
        preprocess_algorithm_params: dict[str, Any] | None,
        preprocess_enable_gamma: bool | None,
    ) -> ResolvedDetectionConfig:
        mode = self._normalize_mode(recognition_mode)
        if mode == "image":
            return self._build_image_config(
                weather_scene,
                confidence_threshold,
                iou_threshold,
                preprocess_mode,
                preprocess_profile,
                preprocess_algorithms,
                preprocess_algorithm_params,
                preprocess_enable_gamma,
            )
        return self._build_scene_default_config(
            weather_scene,
            confidence_threshold,
            iou_threshold,
            preprocess_mode,
            preprocess_profile,
            preprocess_algorithms,
            preprocess_algorithm_params,
            preprocess_enable_gamma,
        )

    def _normalize_mode(self, recognition_mode: str | None) -> str:
        candidate = recognition_mode or settings.DETECTION_DEFAULT_RECOGNITION_MODE
        return candidate if candidate in SUPPORTED_RECOGNITION_MODES else "scene_default"

    def _normalize_scene(self, weather_scene: str | None, fallback: str) -> str:
        candidate = weather_scene or fallback
        return candidate if candidate in SUPPORTED_WEATHER_SCENES else fallback

    def _build_image_config(
        self,
        weather_scene: str | None,
        confidence_threshold: float | None,
        iou_threshold: float | None,
        preprocess_mode: str | None,
        preprocess_profile: str | None,
        preprocess_algorithms: list[str] | None,
        preprocess_algorithm_params: dict[str, Any] | None,
        preprocess_enable_gamma: bool | None,
    ) -> ResolvedDetectionConfig:
        return ResolvedDetectionConfig(
            recognition_mode="image",
            weather_scene=self._normalize_scene(weather_scene, "unknown"),
            confidence_threshold=confidence_threshold if confidence_threshold is not None else 0.25,
            iou_threshold=iou_threshold if iou_threshold is not None else 0.45,
            preprocess_mode=preprocess_mode or "off",
            preprocess_profile=preprocess_profile or "",
            preprocess_algorithms=list(preprocess_algorithms or []),
            preprocess_algorithm_params=dict(preprocess_algorithm_params or {}),
            preprocess_enable_gamma=bool(preprocess_enable_gamma) if preprocess_enable_gamma is not None else False,
            runtime_options={
                "source_profile": "image_upload",
                "model_profile": "image_standard",
                "image_size": 640,
                "augment": False,
            },
        )

    def _build_scene_default_config(
        self,
        weather_scene: str | None,
        confidence_threshold: float | None,
        iou_threshold: float | None,
        preprocess_mode: str | None,
        preprocess_profile: str | None,
        preprocess_algorithms: list[str] | None,
        preprocess_algorithm_params: dict[str, Any] | None,
        preprocess_enable_gamma: bool | None,
    ) -> ResolvedDetectionConfig:
        return ResolvedDetectionConfig(
            recognition_mode="scene_default",
            weather_scene=self._normalize_scene(weather_scene, settings.DETECTION_DEFAULT_SCENE),
            confidence_threshold=(
                confidence_threshold
                if confidence_threshold is not None
                else settings.DETECTION_SCENE_CONFIDENCE_THRESHOLD
            ),
            iou_threshold=iou_threshold if iou_threshold is not None else settings.DETECTION_SCENE_IOU_THRESHOLD,
            preprocess_mode=preprocess_mode or settings.DETECTION_SCENE_PREPROCESS_MODE,
            preprocess_profile=preprocess_profile or settings.DETECTION_SCENE_PREPROCESS_PROFILE,
            preprocess_algorithms=list(preprocess_algorithms or []),
            preprocess_algorithm_params=dict(preprocess_algorithm_params or {}),
            preprocess_enable_gamma=(
                bool(preprocess_enable_gamma)
                if preprocess_enable_gamma is not None
                else settings.DETECTION_SCENE_PREPROCESS_ENABLE_GAMMA
            ),
            runtime_options={
                "source_profile": "scene_default",
                "model_profile": settings.DETECTION_SCENE_MODEL_PROFILE,
                "image_size": settings.DETECTION_SCENE_IMAGE_SIZE,
                "augment": settings.DETECTION_SCENE_ENABLE_AUGMENT,
            },
        )
