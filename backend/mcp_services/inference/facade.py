from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from mcp_services.common.errors import MCPFacadeError

from inference_service.schemas.inference import InferenceRequest
from inference_service.services.inference import InferencePipeline

from .schemas import (
    RunInferenceInput,
    RunInferenceResult,
    RuntimeCapabilitiesModel,
    RuntimeHealthModel,
)


class InferenceMCPFacade:
    """封裝推理流程，讓 MCP 層只處理協議與結構化輸出。"""

    def __init__(self, pipeline: InferencePipeline | None = None) -> None:
        self.pipeline = pipeline or InferencePipeline()

    def run_inference(self, payload: RunInferenceInput) -> RunInferenceResult:
        image_path = Path(payload.image_path)
        if not image_path.exists():
            raise MCPFacadeError(f"找不到待推理圖片：{image_path}")

        request_payload = payload.model_copy(
            update={"task_no": payload.task_no or self._generate_task_no()}
        )
        request = InferenceRequest(**request_payload.model_dump())
        result = self.pipeline.detect(request)
        return RunInferenceResult.model_validate(self._normalize_result(result))

    def get_current_model(self) -> dict:
        return self._normalize_result(self.pipeline.current_model())

    def get_runtime_health(self) -> RuntimeHealthModel:
        model = self.get_current_model()
        ready = bool(model.get("ready", False))
        return RuntimeHealthModel(
            status="ok" if ready else "degraded",
            service="inference-mcp",
            ready=ready,
            engine_type=str(model.get("engine_type", "unknown")),
            model_name=str(model.get("model_name", "")),
            model_version=str(model.get("model_version", "")),
        )

    def get_runtime_capabilities(self) -> RuntimeCapabilitiesModel:
        return RuntimeCapabilitiesModel(
            recognition_modes=["image", "scene_default"],
            scenes=["unknown", "rain", "fog", "rain_fog"],
            preprocess_modes=["off", "auto", "manual"],
            supports_runtime_options=True,
            supports_mock=True,
        )

    def _generate_task_no(self) -> str:
        return f"MCPINF-{uuid4().hex[:12].upper()}"

    def _normalize_result(self, value):
        if hasattr(value, "model_dump"):
            return value.model_dump()
        return value
