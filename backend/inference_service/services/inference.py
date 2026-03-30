from inference_service.adapters.base import BaseInferenceAdapter
from inference_service.adapters.mock import MockInferenceAdapter
from inference_service.adapters.yolov13 import YoloV13InferenceAdapter
from inference_service.core.config import settings
from inference_service.schemas.inference import InferenceRequest


class InferencePipeline:
    def __init__(self) -> None:
        self.adapter = self._build_adapter()

    def _build_adapter(self) -> BaseInferenceAdapter:
        if settings.model_mode == "yolov13":
            return YoloV13InferenceAdapter(settings)
        return MockInferenceAdapter(settings)

    def current_model(self) -> dict:
        try:
            return self.adapter.describe()
        except Exception as exc:  # noqa: BLE001
            return {"engine_type": settings.model_mode, "ready": False, "error": str(exc)}

    def detect(self, payload: InferenceRequest):
        return self.adapter.detect(payload)
