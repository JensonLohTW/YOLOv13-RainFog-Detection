from inference_service.adapters.mock import MockInferenceAdapter
from inference_service.schemas.inference import InferenceRequest
from inference_service.services.runtime_context import build_runtime_context


def test_build_runtime_context_reads_scene_mode_options() -> None:
    payload = InferenceRequest(
        task_no="DT202603300001",
        image_path="/tmp/sample.jpg",
        recognition_mode="scene_default",
        runtime_options={
            "source_profile": "scene_default",
            "model_profile": "scene_v2",
            "image_size": 960,
            "augment": True,
        },
    )
    context = build_runtime_context(payload)
    assert context.recognition_mode == "scene_default"
    assert context.source_profile == "scene_default"
    assert context.model_profile == "scene_v2"
    assert context.image_size == 960
    assert context.augment is True


def test_mock_adapter_preserves_mode_metadata() -> None:
    payload = InferenceRequest(
        task_no="DT202603300002",
        image_path="/tmp/sample.jpg",
        recognition_mode="scene_default",
        scene="rain_fog",
        runtime_options={
            "source_profile": "scene_default",
            "model_profile": "scene_v2",
            "image_size": 960,
            "augment": True,
        },
    )
    result = MockInferenceAdapter().detect(payload)
    assert result["model_version"] == "scene_v2"
    assert result["raw"]["recognition_mode"] == "scene_default"
    assert result["raw"]["runtime_options"]["image_size"] == 960
