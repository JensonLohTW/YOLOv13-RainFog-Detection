from dataclasses import dataclass

from inference_service.schemas.inference import InferenceRequest


@dataclass(frozen=True)
class InferenceRuntimeContext:
    recognition_mode: str
    source_profile: str
    model_profile: str
    image_size: int
    augment: bool


def build_runtime_context(payload: InferenceRequest) -> InferenceRuntimeContext:
    options = dict(payload.runtime_options)
    return InferenceRuntimeContext(
        recognition_mode=payload.recognition_mode,
        source_profile=str(options.get("source_profile", "image_upload")),
        model_profile=str(options.get("model_profile", "image_standard")),
        image_size=int(options.get("image_size", 640)),
        augment=bool(options.get("augment", False)),
    )
