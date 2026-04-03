from __future__ import annotations

from pydantic import BaseModel, Field


class CreateTrainingJobInput(BaseModel):
    dataset_id: int
    model_file: str = "yolov13l.pt"
    epochs: int = Field(default=50, ge=1, le=500)
    batch: int = Field(default=4, ge=1)
    imgsz: int = Field(default=640, ge=32)
    device: str = "0"
    workers: int = Field(default=0, ge=0)
    patience: int = Field(default=20, ge=1)
    preprocess_mode: str = "off"
    preprocess_profile: str = ""
    preprocess_algorithms: list[str] = Field(default_factory=list)
    preprocess_algorithm_params: dict = Field(default_factory=dict)
    preprocess_enable_gamma: bool = False


class DeployTrainingModelInput(BaseModel):
    job_id: int
    model_alias: str = ""
