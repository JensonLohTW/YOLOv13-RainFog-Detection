from __future__ import annotations

import argparse
from typing import Any

from common.weather_preprocess import PreprocessOptions


def add_preprocess_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--preprocess-mode", default="off", choices=["off", "auto", "manual"], help="图像预处理策略")
    parser.add_argument("--preprocess-profile", default="", help="手动指定场景模板：sandstorm / fog / rain / snow")
    parser.add_argument("--preprocess-scene", default="", help="推理或验证时的场景提示")
    parser.add_argument("--preprocess-algorithms", default="", help="手动算法列表，逗号分隔")
    parser.add_argument("--preprocess-enable-gamma", action="store_true", help="在当前策略中追加 gamma 校正")
    parser.add_argument("--prepared-datasets-root", default="", help="预处理派生数据集输出根目录")
    parser.add_argument("--preprocess-overwrite", action="store_true", help="重新生成派生预处理数据集")


def parse_csv_algorithms(value: str | list[str] | tuple[str, ...] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item.strip() for item in str(value).split(",") if item.strip()]


def build_preprocess_options(args: argparse.Namespace, config: dict[str, Any] | None = None) -> PreprocessOptions:
    preprocess_cfg = (config or {}).get("preprocess", {}) if isinstance(config, dict) else {}
    algorithms = parse_csv_algorithms(getattr(args, "preprocess_algorithms", "")) or parse_csv_algorithms(preprocess_cfg.get("algorithms"))
    return PreprocessOptions(
        mode=getattr(args, "preprocess_mode", preprocess_cfg.get("mode", "off")),
        profile=getattr(args, "preprocess_profile", preprocess_cfg.get("profile", "")) or preprocess_cfg.get("profile", ""),
        scene=getattr(args, "preprocess_scene", preprocess_cfg.get("scene", "")) or preprocess_cfg.get("scene", ""),
        algorithms=algorithms,
        algorithm_params=dict(preprocess_cfg.get("algorithm_params", {})),
        enable_gamma=bool(getattr(args, "preprocess_enable_gamma", False) or preprocess_cfg.get("enable_gamma", False)),
    )


def preprocess_summary(options: PreprocessOptions) -> dict[str, Any]:
    return options.to_dict()
