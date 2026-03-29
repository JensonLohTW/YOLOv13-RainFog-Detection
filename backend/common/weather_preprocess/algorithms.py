from __future__ import annotations

from collections.abc import Callable
from typing import Any

import cv2
import numpy as np

DEFAULT_SCENE_ALGORITHMS = {
    "sandstorm": ["white_balance", "dcp_dehaze", "clahe", "guided_filter"],
    "fog": ["dcp_dehaze", "clahe", "mild_unsharp"],
    "rain": ["bilateral", "tone_mapping", "clahe"],
    "snow": ["highlight_compression", "clahe", "bilateral", "mild_unsharp"],
}

DEFAULT_ALGORITHM_PARAMS = {
    "white_balance": {"strength": 1.0},
    "dcp_dehaze": {"omega": 0.92, "t_min": 0.14, "kernel_size": 15, "percentile": 0.001},
    "clahe": {"clip_limit": 2.5, "tile_grid_size": 8},
    "guided_filter": {"radius": 30, "eps": 0.01},
    "bilateral": {"d": 7, "sigma_color": 60.0, "sigma_space": 60.0},
    "tone_mapping": {"gamma": 1.15, "saturation": 1.02, "highlight_strength": 0.25},
    "gamma": {"gamma": 1.25},
    "highlight_compression": {"strength": 0.4},
    "mild_unsharp": {"sigma": 1.2, "amount": 0.9, "threshold": 3},
}


def _ensure_uint8_rgb(image: np.ndarray) -> np.ndarray:
    if image.dtype == np.uint8:
        return image
    clipped = np.clip(image, 0, 255)
    return clipped.astype(np.uint8)


def _merge_params(name: str, overrides: dict[str, Any] | None) -> dict[str, Any]:
    params = dict(DEFAULT_ALGORITHM_PARAMS.get(name, {}))
    if overrides:
        params.update(overrides)
    return params


def white_balance_gray_world(image: np.ndarray, strength: float = 1.0) -> np.ndarray:
    img = image.astype(np.float32)
    means = img.reshape(-1, 3).mean(axis=0)
    gray = float(np.mean(means))
    scale = gray / np.maximum(means, 1e-6)
    scale = 1.0 + (scale - 1.0) * float(strength)
    balanced = img * scale.reshape(1, 1, 3)
    return _ensure_uint8_rgb(balanced)


def dehaze_dcp(
    image: np.ndarray,
    omega: float = 0.92,
    t_min: float = 0.14,
    kernel_size: int = 15,
    percentile: float = 0.001,
) -> np.ndarray:
    bgr = cv2.cvtColor(_ensure_uint8_rgb(image), cv2.COLOR_RGB2BGR)
    img = bgr.astype(np.float32)
    kernel_size = max(3, int(kernel_size) | 1)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
    dark = cv2.erode(np.min(img, axis=2), kernel)
    flat_dark = dark.reshape(-1)
    flat_img = img.reshape(-1, 3)
    top_n = max(1, int(flat_dark.size * max(float(percentile), 1e-5)))
    indices = np.argpartition(flat_dark, -top_n)[-top_n:]
    atmospheric = np.mean(flat_img[indices], axis=0)
    atmospheric = np.maximum(atmospheric, 1.0)
    normalized = img / atmospheric.reshape(1, 1, 3)
    transmission = 1.0 - float(omega) * cv2.erode(np.min(normalized, axis=2), kernel)
    transmission = np.clip(transmission, float(t_min), 1.0)
    transmission = cv2.bilateralFilter(transmission.astype(np.float32), 9, 50, 50)
    restored = (img - atmospheric.reshape(1, 1, 3)) / transmission[:, :, None] + atmospheric.reshape(1, 1, 3)
    restored = np.clip(restored, 0, 255).astype(np.uint8)
    return cv2.cvtColor(restored, cv2.COLOR_BGR2RGB)


def clahe_on_l_channel(image: np.ndarray, clip_limit: float = 2.5, tile_grid_size: int = 8) -> np.ndarray:
    lab = cv2.cvtColor(_ensure_uint8_rgb(image), cv2.COLOR_RGB2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=float(clip_limit), tileGridSize=(int(tile_grid_size), int(tile_grid_size)))
    enhanced = clahe.apply(l)
    merged = cv2.merge((enhanced, a, b))
    return cv2.cvtColor(merged, cv2.COLOR_LAB2RGB)


def bilateral_filter(
    image: np.ndarray,
    d: int = 7,
    sigma_color: float = 60.0,
    sigma_space: float = 60.0,
) -> np.ndarray:
    filtered = cv2.bilateralFilter(_ensure_uint8_rgb(image), int(d), float(sigma_color), float(sigma_space))
    return _ensure_uint8_rgb(filtered)


def guided_filter_smooth(image: np.ndarray, radius: int = 30, eps: float = 0.01) -> np.ndarray:
    rgb = _ensure_uint8_rgb(image)
    if hasattr(cv2, "ximgproc") and hasattr(cv2.ximgproc, "guidedFilter"):
        guide = rgb.astype(np.float32) / 255.0
        src = guide.copy()
        filtered = cv2.ximgproc.guidedFilter(guide=guide, src=src, radius=int(radius), eps=float(eps))
        return _ensure_uint8_rgb(filtered * 255.0)
    sigma = max(10.0, float(radius) * 1.8)
    return bilateral_filter(rgb, d=9, sigma_color=sigma, sigma_space=sigma)


def unsharp_mask(image: np.ndarray, sigma: float = 1.2, amount: float = 0.9, threshold: int = 3) -> np.ndarray:
    rgb = _ensure_uint8_rgb(image)
    blurred = cv2.GaussianBlur(rgb, (0, 0), float(sigma))
    sharpened = cv2.addWeighted(rgb, 1.0 + float(amount), blurred, -float(amount), 0)
    diff = np.abs(rgb.astype(np.int16) - blurred.astype(np.int16))
    mask = (diff.max(axis=2) >= int(threshold))[:, :, None]
    result = np.where(mask, sharpened, rgb)
    return _ensure_uint8_rgb(result)


def tone_mapping(
    image: np.ndarray,
    gamma: float = 1.15,
    saturation: float = 1.02,
    highlight_strength: float = 0.25,
) -> np.ndarray:
    rgb = _ensure_uint8_rgb(image).astype(np.float32) / 255.0
    luminance = np.max(rgb, axis=2, keepdims=True)
    compressed = rgb / (1.0 + np.maximum(luminance - 0.55, 0.0) * (1.5 + float(highlight_strength) * 2.0))
    compressed = np.clip(compressed, 0.0, 1.0)
    mapped = np.power(compressed, 1.0 / max(float(gamma), 1e-6))
    hsv = cv2.cvtColor((mapped * 255.0).astype(np.uint8), cv2.COLOR_RGB2HSV).astype(np.float32)
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * float(saturation), 0, 255)
    return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)


def gamma_correction(image: np.ndarray, gamma: float = 1.25) -> np.ndarray:
    rgb = _ensure_uint8_rgb(image).astype(np.float32) / 255.0
    corrected = np.power(rgb, 1.0 / max(float(gamma), 1e-6))
    return _ensure_uint8_rgb(corrected * 255.0)


def highlight_compression(image: np.ndarray, strength: float = 0.4) -> np.ndarray:
    hsv = cv2.cvtColor(_ensure_uint8_rgb(image), cv2.COLOR_RGB2HSV).astype(np.float32)
    value = hsv[:, :, 2] / 255.0
    cutoff = 0.7
    over = np.maximum(value - cutoff, 0.0)
    value = np.where(value > cutoff, cutoff + over / (1.0 + over * (2.0 + float(strength) * 3.0)), value)
    hsv[:, :, 2] = np.clip(value * 255.0, 0, 255)
    return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)


ALGORITHM_REGISTRY: dict[str, Callable[..., np.ndarray]] = {
    "white_balance": white_balance_gray_world,
    "dcp_dehaze": dehaze_dcp,
    "clahe": clahe_on_l_channel,
    "guided_filter": guided_filter_smooth,
    "bilateral": bilateral_filter,
    "tone_mapping": tone_mapping,
    "gamma": gamma_correction,
    "highlight_compression": highlight_compression,
    "mild_unsharp": unsharp_mask,
}


def get_supported_algorithms() -> list[str]:
    return sorted(ALGORITHM_REGISTRY.keys())


def normalize_algorithms(algorithms: list[str] | tuple[str, ...] | None) -> list[str]:
    if not algorithms:
        return []
    normalized: list[str] = []
    for name in algorithms:
        value = str(name).strip().lower()
        if value and value in ALGORITHM_REGISTRY and value not in normalized:
            normalized.append(value)
    return normalized


def apply_algorithm_chain(
    image: np.ndarray,
    algorithms: list[str],
    algorithm_params: dict[str, dict[str, Any]] | None = None,
) -> np.ndarray:
    output = _ensure_uint8_rgb(image)
    for name in normalize_algorithms(algorithms):
        func = ALGORITHM_REGISTRY[name]
        params = _merge_params(name, (algorithm_params or {}).get(name))
        output = func(output, **params)
    return _ensure_uint8_rgb(output)
