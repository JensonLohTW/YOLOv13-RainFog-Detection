from typing import List

from pydantic import BaseModel, Field


class DetectionObject(BaseModel):
    class_id: int
    class_name: str
    confidence: float
    bbox: List[int] = Field(min_length=4, max_length=4)


class InferenceRequest(BaseModel):
    task_no: str
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


class InferenceResponse(BaseModel):
    task_no: str
    success: bool
    engine_type: str
    engine_version: str
    model_name: str
    model_version: str
    duration_ms: int
    result_image_path: str
    objects: list[DetectionObject]
    raw: dict
