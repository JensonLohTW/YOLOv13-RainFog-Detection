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
        "config_key": "detection_default_recognition_mode",
        "config_value": settings.DETECTION_DEFAULT_RECOGNITION_MODE,
        "value_type": SystemConfigItem.ValueType.STRING,
        "description": "Default recognition mode for task creation",
    },
    {
        "config_key": "detection_default_scene",
        "config_value": settings.DETECTION_DEFAULT_SCENE,
        "value_type": SystemConfigItem.ValueType.STRING,
        "description": "Default weather scene used by scene mode",
    },
    {
        "config_key": "detection_scene_confidence_threshold",
        "config_value": str(settings.DETECTION_SCENE_CONFIDENCE_THRESHOLD),
        "value_type": SystemConfigItem.ValueType.FLOAT,
        "description": "Default confidence threshold for scene mode",
    },
    {
        "config_key": "detection_scene_iou_threshold",
        "config_value": str(settings.DETECTION_SCENE_IOU_THRESHOLD),
        "value_type": SystemConfigItem.ValueType.FLOAT,
        "description": "Default IOU threshold for scene mode",
    },
    {
        "config_key": "detection_scene_preprocess_mode",
        "config_value": settings.DETECTION_SCENE_PREPROCESS_MODE,
        "value_type": SystemConfigItem.ValueType.STRING,
        "description": "Default preprocess mode for scene mode",
    },
    {
        "config_key": "detection_scene_preprocess_profile",
        "config_value": settings.DETECTION_SCENE_PREPROCESS_PROFILE,
        "value_type": SystemConfigItem.ValueType.STRING,
        "description": "Default preprocess profile for scene mode",
    },
    {
        "config_key": "detection_scene_model_profile",
        "config_value": settings.DETECTION_SCENE_MODEL_PROFILE,
        "value_type": SystemConfigItem.ValueType.STRING,
        "description": "Default model profile for scene mode",
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
            "detection_defaults": {
                "recognition_mode": items["detection_default_recognition_mode"].config_value,
                "scene": items["detection_default_scene"].config_value,
                "confidence_threshold": float(items["detection_scene_confidence_threshold"].config_value),
                "iou_threshold": float(items["detection_scene_iou_threshold"].config_value),
                "preprocess_mode": items["detection_scene_preprocess_mode"].config_value,
                "preprocess_profile": items["detection_scene_preprocess_profile"].config_value,
                "model_profile": items["detection_scene_model_profile"].config_value,
            },
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
