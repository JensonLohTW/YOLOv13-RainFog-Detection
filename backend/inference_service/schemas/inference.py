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
    confidence_threshold: float = 0.25
    iou_threshold: float = 0.45
    scene: str = "unknown"
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
