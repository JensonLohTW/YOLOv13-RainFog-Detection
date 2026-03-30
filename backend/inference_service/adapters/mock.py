from inference_service.schemas.inference import InferenceRequest
from inference_service.services.runtime_context import build_runtime_context


class MockInferenceAdapter:
    def describe(self):
        return {
            "engine_type": "mock",
            "model_name": "yolov13-rainfog",
            "model_version": "draft",
            "ready": True,
        }

    def detect(self, payload: InferenceRequest):
        preprocess = {
            "mode": payload.preprocess_mode,
            "profile": payload.preprocess_profile,
            "algorithms": list(payload.preprocess_algorithms),
            "algorithm_params": dict(payload.preprocess_algorithm_params),
            "enable_gamma": payload.preprocess_enable_gamma,
        }
        runtime_context = build_runtime_context(payload)
        if "." in payload.image_path:
            stem, suffix = payload.image_path.rsplit(".", 1)
            result_image_path = f"{stem}_result.{suffix}"
        else:
            result_image_path = payload.image_path + "_result"
        return {
            "task_no": payload.task_no,
            "success": True,
            "engine_type": "mock",
            "engine_version": "0.1.0",
            "model_name": "yolov13-rainfog",
            "model_version": runtime_context.model_profile,
            "duration_ms": 128,
            "result_image_path": result_image_path,
            "objects": [
                {
                    "class_id": 0,
                    "class_name": "car",
                    "confidence": 0.92,
                    "bbox": [120, 80, 360, 240],
                }
            ],
            "raw": {
                "mock": True,
                "scene": payload.scene,
                "recognition_mode": payload.recognition_mode,
                "preprocess": preprocess,
                "runtime_options": payload.runtime_options,
            },
        }
