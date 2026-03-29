from __future__ import annotations

from pathlib import Path

RAW_SCENE_LABELS = (
    "dusttornado",
    "foggy",
    "haze",
    "mist",
    "rain_storm",
    "sand_storm",
    "snow_storm",
)

STRATEGY_SCENES = ("sandstorm", "fog", "rain", "snow", "unknown")

_SCENE_MAPPING = {
    "dusttornado": "sandstorm",
    "sand_storm": "sandstorm",
    "foggy": "fog",
    "haze": "fog",
    "mist": "fog",
    "rain_storm": "rain",
    "snow_storm": "snow",
}


def detect_raw_scene_label(image_path: str | Path) -> str:
    path = Path(image_path)
    tokens = [path.name.lower(), path.stem.lower()]
    tokens.extend(part.lower() for part in path.parts)
    for label in sorted(RAW_SCENE_LABELS, key=len, reverse=True):
        if any(label in token for token in tokens):
            return label
    return "unknown"


def map_scene_label(raw_scene_label: str) -> str:
    return _SCENE_MAPPING.get(str(raw_scene_label).lower(), "unknown")


def detect_strategy_scene(image_path: str | Path) -> tuple[str, str]:
    raw_scene = detect_raw_scene_label(image_path)
    return raw_scene, map_scene_label(raw_scene)
