from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np


@dataclass
class HeuristicSceneInference:
    scene: str
    source: str
    debug: dict[str, Any]


def infer_scene_from_image(image: np.ndarray) -> HeuristicSceneInference:
    rgb = np.clip(image, 0, 255).astype(np.uint8)
    gray_u8 = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    gray = gray_u8.astype(np.float32) / 255.0
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV).astype(np.float32)

    brightness_mean = float(np.mean(gray))
    brightness_std = float(np.std(gray))
    saturation_mean = float(np.mean(hsv[..., 1] / 255.0))
    edge_density = float(np.mean(cv2.Canny(gray_u8, 80, 160) > 0))
    laplacian_var = float(cv2.Laplacian(gray, cv2.CV_32F).var())
    highlight_ratio = float(np.mean(gray > 0.82))

    rgb_mean = rgb.astype(np.float32).reshape(-1, 3).mean(axis=0) / 255.0
    red_mean = float(rgb_mean[0])
    green_mean = float(rgb_mean[1])
    blue_mean = float(rgb_mean[2])
    warm_bias = float(((red_mean + green_mean) / 2.0) - blue_mean)

    scores = {
        "fog": 0.0,
        "rain": 0.0,
        "sandstorm": 0.0,
        "snow": 0.0,
    }

    if brightness_std < 0.18:
        scores["fog"] += 1.5
    if edge_density < 0.09:
        scores["fog"] += 1.5
    if laplacian_var < 0.015:
        scores["fog"] += 1.0
    if brightness_mean > 0.48:
        scores["fog"] += 0.5

    if brightness_mean < 0.58:
        scores["rain"] += 1.2
    if edge_density > 0.09:
        scores["rain"] += 1.3
    if saturation_mean < 0.42:
        scores["rain"] += 0.8
    if 0.12 <= brightness_std <= 0.3:
        scores["rain"] += 0.7

    if highlight_ratio > 0.2:
        scores["snow"] += 1.8
    if brightness_mean > 0.7:
        scores["snow"] += 1.2
    if saturation_mean < 0.35:
        scores["snow"] += 0.8
    if edge_density < 0.14:
        scores["snow"] += 0.5

    if warm_bias > 0.06:
        scores["sandstorm"] += 1.7
    if saturation_mean < 0.5:
        scores["sandstorm"] += 0.8
    if brightness_std < 0.2:
        scores["sandstorm"] += 0.8
    if edge_density < 0.11:
        scores["sandstorm"] += 0.7

    scene, score = max(scores.items(), key=lambda item: item[1])
    detected_scene = scene if score >= 2.6 else "unknown"

    debug = {
        "brightness_mean": round(brightness_mean, 4),
        "brightness_std": round(brightness_std, 4),
        "saturation_mean": round(saturation_mean, 4),
        "edge_density": round(edge_density, 4),
        "laplacian_var": round(laplacian_var, 4),
        "highlight_ratio": round(highlight_ratio, 4),
        "warm_bias": round(warm_bias, 4),
        "red_mean": round(red_mean, 4),
        "green_mean": round(green_mean, 4),
        "blue_mean": round(blue_mean, 4),
        "scores": {name: round(value, 4) for name, value in scores.items()},
    }

    if detected_scene == "unknown":
        return HeuristicSceneInference(scene="unknown", source="unknown", debug=debug)
    return HeuristicSceneInference(scene=detected_scene, source="image_heuristic", debug=debug)
