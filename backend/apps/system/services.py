from django.conf import settings

from integrations.inference.client import InferenceServiceClient

from .models import SystemConfigItem

DEFAULT_CONFIGS = [
    {
        "config_key": "inference_base_url",
        "config_value": settings.INFERENCE_BASE_URL,
        "value_type": SystemConfigItem.ValueType.URL,
        "description": "FastAPI inference service base URL",
    },
    {
        "config_key": "inference_use_mock",
        "config_value": "true" if settings.INFERENCE_USE_MOCK else "false",
        "value_type": SystemConfigItem.ValueType.BOOLEAN,
        "description": "Whether to use mock inference mode",
    },
    {
        "config_key": "inference_model_mode",
        "config_value": "mock" if settings.INFERENCE_USE_MOCK else "yolov13",
        "value_type": SystemConfigItem.ValueType.STRING,
        "description": "Current inference adapter mode",
    },
    {
        "config_key": "inference_model_name",
        "config_value": "yolov13-rainfog",
        "value_type": SystemConfigItem.ValueType.STRING,
        "description": "Current inference model name",
    },
    {
        "config_key": "redis_host",
        "config_value": settings.REDIS_HOST,
        "value_type": SystemConfigItem.ValueType.STRING,
        "description": "Redis host",
    },
    {
        "config_key": "redis_port",
        "config_value": str(settings.REDIS_PORT),
        "value_type": SystemConfigItem.ValueType.INTEGER,
        "description": "Redis port",
    },
    {
        "config_key": "redis_db",
        "config_value": str(settings.REDIS_DB),
        "value_type": SystemConfigItem.ValueType.INTEGER,
        "description": "Redis database index",
    },
]


class SystemConfigService:
    def __init__(self) -> None:
        self.inference_client = InferenceServiceClient()

    def ensure_defaults(self) -> None:
        for item in DEFAULT_CONFIGS:
            SystemConfigItem.objects.get_or_create(config_key=item["config_key"], defaults=item)

    def list_items(self):
        self.ensure_defaults()
        return SystemConfigItem.objects.all()

    def summary(self) -> dict:
        items = {item.config_key: item for item in self.list_items()}
        return {
            "inference_base_url": items["inference_base_url"].config_value,
            "inference_use_mock": items["inference_use_mock"].config_value.lower() == "true",
            "inference_model_mode": items["inference_model_mode"].config_value,
            "inference_model_name": items["inference_model_name"].config_value,
            "redis": {
                "host": items["redis_host"].config_value,
                "port": int(items["redis_port"].config_value),
                "db": int(items["redis_db"].config_value),
            },
            "runtime": self.inference_client.get_runtime_summary(),
        }

    def update_item(self, item: SystemConfigItem, value: str, user=None) -> SystemConfigItem:  # noqa: ANN001
        item.config_value = value
        item.updated_by = user if getattr(user, "is_authenticated", False) else None
        item.save(update_fields=["config_value", "updated_by", "updated_at"])
        return item
