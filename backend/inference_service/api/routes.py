from fastapi import APIRouter

from inference_service.schemas.inference import InferenceRequest, InferenceResponse
from inference_service.services.inference import InferencePipeline

router = APIRouter(prefix="/internal")
pipeline = InferencePipeline()


@router.get("/health")
def health():
    return {"status": "ok", "service": "fastapi-inference"}


@router.get("/models/current")
def current_model():
    return pipeline.current_model()


@router.post("/inference/detect", response_model=InferenceResponse)
def detect(payload: InferenceRequest):
    return pipeline.detect(payload)
