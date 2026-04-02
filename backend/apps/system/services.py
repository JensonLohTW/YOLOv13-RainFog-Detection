from __future__ import annotations

import os
from dataclasses import dataclass

from django.conf import settings

from common.llm import LLMSettings
from integrations.inference.client import InferenceServiceClient

from .models import SystemConfigItem


@dataclass(frozen=True)
class ConfigDefinition:
    config_key: str
    default_value: str
    value_type: str
    description: str
    env_var: str | None = None
    is_sensitive: bool = False


CONFIG_DEFINITIONS = [
    ConfigDefinition(
        config_key="inference_base_url",
        default_value=settings.INFERENCE_BASE_URL,
        value_type=SystemConfigItem.ValueType.URL,
        description="FastAPI inference service base URL",
    ),
    ConfigDefinition(
        config_key="inference_use_mock",
        default_value="true" if settings.INFERENCE_USE_MOCK else "false",
        value_type=SystemConfigItem.ValueType.BOOLEAN,
        description="Whether to use mock inference mode",
    ),
    ConfigDefinition(
        config_key="inference_model_mode",
        default_value="mock" if settings.INFERENCE_USE_MOCK else "yolov13",
        value_type=SystemConfigItem.ValueType.STRING,
        description="Current inference adapter mode",
    ),
    ConfigDefinition(
        config_key="inference_model_name",
        default_value="yolov13-rainfog",
        value_type=SystemConfigItem.ValueType.STRING,
        description="Current inference model name",
    ),
    ConfigDefinition(
        config_key="detection_default_recognition_mode",
        default_value=settings.DETECTION_DEFAULT_RECOGNITION_MODE,
        value_type=SystemConfigItem.ValueType.STRING,
        description="Default recognition mode for task creation",
    ),
    ConfigDefinition(
        config_key="detection_default_scene",
        default_value=settings.DETECTION_DEFAULT_SCENE,
        value_type=SystemConfigItem.ValueType.STRING,
        description="Default weather scene used by scene mode",
    ),
    ConfigDefinition(
        config_key="detection_scene_confidence_threshold",
        default_value=str(settings.DETECTION_SCENE_CONFIDENCE_THRESHOLD),
        value_type=SystemConfigItem.ValueType.FLOAT,
        description="Default confidence threshold for scene mode",
    ),
    ConfigDefinition(
        config_key="detection_scene_iou_threshold",
        default_value=str(settings.DETECTION_SCENE_IOU_THRESHOLD),
        value_type=SystemConfigItem.ValueType.FLOAT,
        description="Default IOU threshold for scene mode",
    ),
    ConfigDefinition(
        config_key="detection_scene_preprocess_mode",
        default_value=settings.DETECTION_SCENE_PREPROCESS_MODE,
        value_type=SystemConfigItem.ValueType.STRING,
        description="Default preprocess mode for scene mode",
    ),
    ConfigDefinition(
        config_key="detection_scene_preprocess_profile",
        default_value=settings.DETECTION_SCENE_PREPROCESS_PROFILE,
        value_type=SystemConfigItem.ValueType.STRING,
        description="Default preprocess profile for scene mode",
    ),
    ConfigDefinition(
        config_key="detection_scene_model_profile",
        default_value=settings.DETECTION_SCENE_MODEL_PROFILE,
        value_type=SystemConfigItem.ValueType.STRING,
        description="Default model profile for scene mode",
    ),
    ConfigDefinition(
        config_key="redis_host",
        default_value=settings.REDIS_HOST,
        value_type=SystemConfigItem.ValueType.STRING,
        description="Redis host",
    ),
    ConfigDefinition(
        config_key="redis_port",
        default_value=str(settings.REDIS_PORT),
        value_type=SystemConfigItem.ValueType.INTEGER,
        description="Redis port",
    ),
    ConfigDefinition(
        config_key="redis_db",
        default_value=str(settings.REDIS_DB),
        value_type=SystemConfigItem.ValueType.INTEGER,
        description="Redis database index",
    ),
    ConfigDefinition(
        config_key="llm_provider",
        default_value=settings.LLM_PROVIDER,
        value_type=SystemConfigItem.ValueType.STRING,
        description="LLM provider identifier, for example mock or openai_compatible",
        env_var="LLM_PROVIDER",
    ),
    ConfigDefinition(
        config_key="llm_base_url",
        default_value=settings.LLM_BASE_URL,
        value_type=SystemConfigItem.ValueType.URL,
        description="LLM API base URL",
        env_var="LLM_BASE_URL",
    ),
    ConfigDefinition(
        config_key="llm_model",
        default_value=settings.LLM_MODEL,
        value_type=SystemConfigItem.ValueType.STRING,
        description="LLM model name used for explanation generation",
        env_var="LLM_MODEL",
    ),
    ConfigDefinition(
        config_key="llm_api_key",
        default_value="",
        value_type=SystemConfigItem.ValueType.STRING,
        description="LLM API key, prefer environment variable override in production",
        env_var="LLM_API_KEY",
        is_sensitive=True,
    ),
    ConfigDefinition(
        config_key="llm_temperature",
        default_value=str(settings.LLM_TEMPERATURE),
        value_type=SystemConfigItem.ValueType.FLOAT,
        description="LLM generation temperature",
        env_var="LLM_TEMPERATURE",
    ),
    ConfigDefinition(
        config_key="llm_max_tokens",
        default_value=str(settings.LLM_MAX_TOKENS),
        value_type=SystemConfigItem.ValueType.INTEGER,
        description="Maximum output tokens for LLM responses",
        env_var="LLM_MAX_TOKENS",
    ),
    ConfigDefinition(
        config_key="llm_timeout",
        default_value=str(settings.LLM_TIMEOUT),
        value_type=SystemConfigItem.ValueType.INTEGER,
        description="LLM request timeout in seconds",
        env_var="LLM_TIMEOUT",
    ),
]

CONFIG_DEFINITION_MAP = {item.config_key: item for item in CONFIG_DEFINITIONS}


class SystemConfigService:
    def __init__(self) -> None:
        self.inference_client = InferenceServiceClient()

    def ensure_defaults(self) -> None:
        for definition in CONFIG_DEFINITIONS:
            item, created = SystemConfigItem.objects.get_or_create(
                config_key=definition.config_key,
                defaults={
                    "config_value": definition.default_value,
                    "value_type": definition.value_type,
                    "description": definition.description,
                    "is_sensitive": definition.is_sensitive,
                },
            )
            if created:
                continue

            updates = []
            if item.value_type != definition.value_type:
                item.value_type = definition.value_type
                updates.append("value_type")
            if item.description != definition.description:
                item.description = definition.description
                updates.append("description")
            if item.is_sensitive != definition.is_sensitive:
                item.is_sensitive = definition.is_sensitive
                updates.append("is_sensitive")
            if updates:
                updates.append("updated_at")
                item.save(update_fields=updates)

    def list_items(self):
        self.ensure_defaults()
        return SystemConfigItem.objects.all()

    def summary(self) -> dict:
        self.ensure_defaults()
        llm_settings = self.get_llm_settings()
        return {
            "inference_base_url": self.get_effective_value("inference_base_url"),
            "inference_use_mock": self.get_effective_value("inference_use_mock").lower() == "true",
            "inference_model_mode": self.get_effective_value("inference_model_mode"),
            "inference_model_name": self.get_effective_value("inference_model_name"),
            "detection_defaults": {
                "recognition_mode": self.get_effective_value("detection_default_recognition_mode"),
                "scene": self.get_effective_value("detection_default_scene"),
                "confidence_threshold": float(self.get_effective_value("detection_scene_confidence_threshold")),
                "iou_threshold": float(self.get_effective_value("detection_scene_iou_threshold")),
                "preprocess_mode": self.get_effective_value("detection_scene_preprocess_mode"),
                "preprocess_profile": self.get_effective_value("detection_scene_preprocess_profile"),
                "model_profile": self.get_effective_value("detection_scene_model_profile"),
            },
            "redis": {
                "host": self.get_effective_value("redis_host"),
                "port": int(self.get_effective_value("redis_port")),
                "db": int(self.get_effective_value("redis_db")),
            },
            "llm": {
                "provider": llm_settings.provider,
                "base_url": llm_settings.base_url,
                "model": llm_settings.model,
                "temperature": llm_settings.temperature,
                "max_tokens": llm_settings.max_tokens,
                "timeout": llm_settings.timeout,
                "api_key_configured": bool(llm_settings.api_key),
                "api_key_source": llm_settings.api_key_source,
                "config_source": llm_settings.config_source,
            },
            "runtime": self.inference_client.get_runtime_summary(),
        }

    def update_item(self, item: SystemConfigItem, value: str, user=None) -> SystemConfigItem:  # noqa: ANN001
        item.config_value = value
        item.updated_by = user if getattr(user, "is_authenticated", False) else None
        item.save(update_fields=["config_value", "updated_by", "updated_at"])
        return item

    def get_effective_value(self, config_key: str) -> str:
        value, _ = self.get_effective_value_with_source(config_key)
        return value

    def get_effective_value_with_source(self, config_key: str) -> tuple[str, str]:
        definition = CONFIG_DEFINITION_MAP[config_key]
        env_value = self._get_env_value(definition)
        if env_value not in {None, ""}:
            return env_value, "env"

        item = SystemConfigItem.objects.filter(config_key=config_key).only("config_value").first()
        if item and item.config_value != "":
            return item.config_value, "system_config"

        return definition.default_value, "default"

    def build_runtime_meta(self, item: SystemConfigItem) -> dict[str, object]:
        definition = CONFIG_DEFINITION_MAP.get(item.config_key)
        env_value = self._get_env_value(definition) if definition else None
        if env_value not in {None, ""}:
            effective_source = "env"
            has_effective_value = True
            display_value = self._mask_value(env_value) if item.is_sensitive else env_value
        elif item.config_value != "":
            effective_source = "system_config"
            has_effective_value = True
            display_value = self._mask_value(item.config_value) if item.is_sensitive else item.config_value
        else:
            effective_source = "default"
            has_effective_value = bool(definition and definition.default_value != "")
            display_value = self._mask_value(definition.default_value) if item.is_sensitive and definition else (
                definition.default_value if definition else item.config_value
            )

        return {
            "effective_source": effective_source,
            "has_effective_value": has_effective_value,
            "display_value": display_value,
        }

    def get_llm_settings(self) -> LLMSettings:
        provider, provider_source = self.get_effective_value_with_source("llm_provider")
        base_url, base_url_source = self.get_effective_value_with_source("llm_base_url")
        model, model_source = self.get_effective_value_with_source("llm_model")
        api_key, api_key_source = self.get_effective_value_with_source("llm_api_key")
        temperature, temperature_source = self.get_effective_value_with_source("llm_temperature")
        max_tokens, max_tokens_source = self.get_effective_value_with_source("llm_max_tokens")
        timeout, timeout_source = self.get_effective_value_with_source("llm_timeout")
        config_sources = {
            provider_source,
            base_url_source,
            model_source,
            temperature_source,
            max_tokens_source,
            timeout_source,
        }
        config_source = "env" if "env" in config_sources else ("system_config" if "system_config" in config_sources else "default")
        return LLMSettings(
            provider=provider,
            base_url=base_url,
            model=model,
            api_key=api_key,
            temperature=float(temperature),
            max_tokens=int(max_tokens),
            timeout=int(timeout),
            api_key_source=api_key_source,
            config_source=config_source,
        )

    def _get_env_value(self, definition: ConfigDefinition | None) -> str | None:
        if definition is None or not definition.env_var:
            return None
        return os.getenv(definition.env_var)

    def _mask_value(self, value: str) -> str:
        if not value:
            return ""
        if len(value) <= 6:
            return "*" * len(value)
        return f"{value[:2]}{'*' * (len(value) - 4)}{value[-2:]}"
