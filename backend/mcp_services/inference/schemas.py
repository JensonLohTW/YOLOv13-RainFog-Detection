from __future__ import annotations

from pydantic import BaseModel, Field


class InferenceObjectModel(BaseModel):
    class_id: int
    class_name: str
    confidence: float
    bbox: list[int] = Field(min_length=4, max_length=4)


class RunInferenceInput(BaseModel):
    task_no: str = ""
    image_path: str
    recognition_mode: str = "image"
    confidence_threshold: float = 0.25
    iou_threshold: float = 0.45
    scene: str = "unknown"
    preprocess_mode: str = "off"
    preprocess_profile: str = ""
    preprocess_algorithms: list[str] = Field(default_factory=list)
    preprocess_algorithm_params: dict = Field(default_factory=dict)
    preprocess_enable_gamma: bool = False
    runtime_options: dict = Field(default_factory=dict)
    mock: bool = True


class RunInferenceResult(BaseModel):
    task_no: str
    success: bool
    engine_type: str
    engine_version: str
    model_name: str
    model_version: str
    duration_ms: int
    result_image_path: str
    objects: list[InferenceObjectModel]
    raw: dict


class RuntimeHealthModel(BaseModel):
    status: str
    service: str
    ready: bool
    engine_type: str
    model_name: str
    model_version: str


class RuntimeCapabilitiesModel(BaseModel):
    recognition_modes: list[str]
    scenes: list[str]
    preprocess_modes: list[str]
    supports_runtime_options: bool
    supports_mock: bool
