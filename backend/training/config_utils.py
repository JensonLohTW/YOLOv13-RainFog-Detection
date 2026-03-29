from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml


def _flatten(prefix: str, value: Any, target: dict[str, Any]) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            next_prefix = f"{prefix}_{key}" if prefix else str(key)
            _flatten(next_prefix, nested, target)
        return
    target[prefix] = value


def load_config_file(config_path: str | None) -> dict[str, Any]:
    if not config_path:
        return {}
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"配置文件不存在：{path}")
    if path.suffix.lower() == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def apply_config_defaults(parser: argparse.ArgumentParser, config: dict[str, Any]) -> None:
    flattened: dict[str, Any] = {}
    _flatten("", config, flattened)
    cleaned = {key: value for key, value in flattened.items() if key}
    if cleaned:
        parser.set_defaults(**cleaned)


def parse_args_with_config(parser: argparse.ArgumentParser, argv: list[str] | None = None) -> tuple[argparse.Namespace, dict[str, Any]]:
    bootstrap = argparse.ArgumentParser(add_help=False)
    bootstrap.add_argument("--config", default="")
    known, _ = bootstrap.parse_known_args(argv)
    config = load_config_file(known.config)
    apply_config_defaults(parser, config)
    args = parser.parse_args(argv)
    return args, config
