from __future__ import annotations

import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseMCPSettings(BaseSettings):
    """MCP 服務的共用設定。"""

    app_name: str = "RainFog MCP Service"
    log_level: str = "INFO"
    streamable_http_path: str = "/mcp"
    json_response: bool = True


class InferenceMCPSettings(BaseMCPSettings):
    """Inference MCP 專用設定。"""

    app_name: str = "RainFog Inference MCP"

    model_config = SettingsConfigDict(
        env_prefix="INFERENCE_MCP_",
        case_sensitive=False,
        extra="ignore",
    )


class TrainingMCPSettings(BaseMCPSettings):
    """Training MCP 專用設定。"""

    app_name: str = "RainFog Training MCP"
    django_settings_module: str = os.environ.get("DJANGO_SETTINGS_MODULE", "config.settings.dev")
    log_tail_lines: int = 100

    model_config = SettingsConfigDict(
        env_prefix="TRAINING_MCP_",
        case_sensitive=False,
        extra="ignore",
    )
