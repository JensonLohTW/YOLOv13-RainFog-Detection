from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from common.weather_preprocess.algorithms import DEFAULT_SCENE_ALGORITHMS, apply_algorithm_chain, normalize_algorithms
from common.weather_preprocess.scene_classifier import infer_scene_from_image
from common.weather_preprocess.scenes import STRATEGY_SCENES, detect_strategy_scene, map_scene_label

PREPROCESS_MODE_OFF = "off"
PREPROCESS_MODE_AUTO = "auto"
PREPROCESS_MODE_MANUAL = "manual"
_VALID_MODES = {PREPROCESS_MODE_OFF, PREPROCESS_MODE_AUTO, PREPROCESS_MODE_MANUAL}


@dataclass
class PreprocessOptions:
    mode: str = PREPROCESS_MODE_OFF
    profile: str = ""
    scene: str = ""
    algorithms: list[str] = field(default_factory=list)
    algorithm_params: dict[str, dict[str, Any]] = field(default_factory=dict)
    enable_gamma: bool = False

    def normalized_mode(self) -> str:
        mode = str(self.mode or PREPROCESS_MODE_OFF).strip().lower()
        return mode if mode in _VALID_MODES else PREPROCESS_MODE_OFF

    def normalized_profile(self) -> str:
        value = str(self.profile or self.scene or "").strip().lower()
        if value in STRATEGY_SCENES:
            return value
        return map_scene_label(value)

    def normalized_algorithms(self) -> list[str]:
        names = normalize_algorithms(self.algorithms)
        if self.enable_gamma and "gamma" not in names:
            names.append("gamma")
        return names

    def is_enabled(self) -> bool:
        return self.normalized_mode() != PREPROCESS_MODE_OFF

    def signature(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True, ensure_ascii=False)
        total = sum(payload.encode("utf-8"))
        return f"pp{total % 100000000:08d}"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["mode"] = self.normalized_mode()
        data["profile"] = self.normalized_profile()
        data["algorithms"] = self.normalized_algorithms()
        return data

    @classmethod
    def from_mapping(cls, data: dict[str, Any] | None) -> "PreprocessOptions":
        if not data:
            return cls()
        mode = data.get("preprocess_mode", data.get("mode", PREPROCESS_MODE_OFF))
        profile = data.get("preprocess_profile", data.get("profile", ""))
        scene = data.get("preprocess_scene", data.get("scene", ""))
        algorithms = data.get("preprocess_algorithms", data.get("algorithms", [])) or []
        if isinstance(algorithms, str):
            algorithms = [item.strip() for item in algorithms.split(",") if item.strip()]
        algorithm_params = data.get("preprocess_algorithm_params", data.get("algorithm_params", {})) or {}
        enable_gamma = bool(data.get("preprocess_enable_gamma", data.get("enable_gamma", False)))
        return cls(
            mode=str(mode),
            profile=str(profile),
            scene=str(scene),
            algorithms=list(algorithms),
            algorithm_params=dict(algorithm_params),
            enable_gamma=enable_gamma,
        )


@dataclass
class SceneResolution:
    raw_scene: str
    scene: str
    scene_source: str
    scene_debug: dict[str, Any] = field(default_factory=dict)


@dataclass
class PreprocessResult:
    image: np.ndarray
    applied: bool
    mode: str
    raw_scene: str
    scene: str
    scene_source: str
    scene_debug: dict[str, Any]
    algorithms: list[str]
    options: dict[str, Any]

    def metadata(self) -> dict[str, Any]:
        return {
            "applied": self.applied,
            "mode": self.mode,
            "raw_scene": self.raw_scene,
            "scene": self.scene,
            "scene_source": self.scene_source,
            "scene_debug": self.scene_debug,
            "algorithms": self.algorithms,
            "options": self.options,
        }


def _load_rgb_image(image_path: str | Path) -> np.ndarray:
    image = Image.open(image_path).convert("RGB")
    return np.array(image)


def _save_rgb_image(image: np.ndarray, image_path: str | Path) -> None:
    target = Path(image_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(image.astype(np.uint8), mode="RGB").save(target)


def _normalize_scene_value(scene: str) -> str:
    value = str(scene or "").strip().lower()
    if value in STRATEGY_SCENES:
        return value
    return map_scene_label(value)


def _resolve_scene(
    image: np.ndarray | None,
    image_path: str | Path | None,
    options: PreprocessOptions,
    scene_hint: str = "",
) -> SceneResolution:
    raw_scene = "unknown"
    detected_scene = "unknown"
    heuristic_debug: dict[str, Any] = {}
    if image_path:
        raw_scene, detected_scene = detect_strategy_scene(image_path)
    hint_scene = _normalize_scene_value(scene_hint)
    profile_scene = options.normalized_profile()
    mode = options.normalized_mode()
    if mode == PREPROCESS_MODE_AUTO:
        if detected_scene != "unknown":
            return SceneResolution(raw_scene=raw_scene, scene=detected_scene, scene_source="filename")
        if image is not None:
            heuristic = infer_scene_from_image(image)
            heuristic_debug = heuristic.debug
            if heuristic.scene != "unknown":
                return SceneResolution(
                    raw_scene=raw_scene,
                    scene=heuristic.scene,
                    scene_source=heuristic.source,
                    scene_debug=heuristic.debug,
                )
        if profile_scene != "unknown":
            return SceneResolution(
                raw_scene=raw_scene,
                scene=profile_scene,
                scene_source="profile",
                scene_debug=heuristic_debug,
            )
        if hint_scene != "unknown":
            return SceneResolution(
                raw_scene=raw_scene,
                scene=hint_scene,
                scene_source="hint",
                scene_debug=heuristic_debug,
            )
        return SceneResolution(
            raw_scene=raw_scene,
            scene="unknown",
            scene_source="unknown",
            scene_debug=heuristic_debug,
        )
    if profile_scene != "unknown":
        return SceneResolution(raw_scene=raw_scene, scene=profile_scene, scene_source="profile")
    if hint_scene != "unknown":
        return SceneResolution(raw_scene=raw_scene, scene=hint_scene, scene_source="hint")
    source = "filename" if detected_scene != "unknown" else "unknown"
    return SceneResolution(raw_scene=raw_scene, scene=detected_scene, scene_source=source)


def _resolve_algorithms(scene: str, options: PreprocessOptions) -> list[str]:
    mode = options.normalized_mode()
    if mode == PREPROCESS_MODE_OFF:
        return []
    manual_algorithms = options.normalized_algorithms()
    if mode == PREPROCESS_MODE_MANUAL and manual_algorithms:
        return manual_algorithms
    if scene in DEFAULT_SCENE_ALGORITHMS:
        algorithms = list(DEFAULT_SCENE_ALGORITHMS[scene])
        if options.enable_gamma and "gamma" not in algorithms:
            algorithms.append("gamma")
        return algorithms
    return manual_algorithms


def preprocess_image(
    image: np.ndarray,
    options: PreprocessOptions | dict[str, Any] | None = None,
    *,
    image_path: str | Path | None = None,
    scene_hint: str = "",
) -> PreprocessResult:
    preprocess_options = options if isinstance(options, PreprocessOptions) else PreprocessOptions.from_mapping(options)
    mode = preprocess_options.normalized_mode()
    scene_resolution = _resolve_scene(image, image_path, preprocess_options, scene_hint=scene_hint)
    algorithms = _resolve_algorithms(scene_resolution.scene, preprocess_options)
    if mode == PREPROCESS_MODE_OFF or not algorithms:
        return PreprocessResult(
            image=image.astype(np.uint8),
            applied=False,
            mode=mode,
            raw_scene=scene_resolution.raw_scene,
            scene=scene_resolution.scene,
            scene_source=scene_resolution.scene_source,
            scene_debug=scene_resolution.scene_debug,
            algorithms=[],
            options=preprocess_options.to_dict(),
        )
    output = apply_algorithm_chain(image.astype(np.uint8), algorithms, preprocess_options.algorithm_params)
    return PreprocessResult(
        image=output,
        applied=True,
        mode=mode,
        raw_scene=scene_resolution.raw_scene,
        scene=scene_resolution.scene,
        scene_source=scene_resolution.scene_source,
        scene_debug=scene_resolution.scene_debug,
        algorithms=algorithms,
        options=preprocess_options.to_dict(),
    )


def preprocess_image_file(
    image_path: str | Path,
    options: PreprocessOptions | dict[str, Any] | None = None,
    *,
    output_path: str | Path | None = None,
    scene_hint: str = "",
) -> PreprocessResult:
    source = Path(image_path)
    image = _load_rgb_image(source)
    result = preprocess_image(image, options, image_path=source, scene_hint=scene_hint)
    if output_path is not None:
        _save_rgb_image(result.image, output_path)
    return result
