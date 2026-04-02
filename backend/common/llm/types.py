from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class LLMSettings:
    provider: str
    base_url: str
    model: str
    api_key: str
    temperature: float
    max_tokens: int
    timeout: int
    api_key_source: str = "none"
    config_source: str = "default"


@dataclass(frozen=True)
class LLMResponse:
    text: str
    provider: str
    model: str
    finish_reason: str = ""
    raw: dict[str, Any] = field(default_factory=dict)
