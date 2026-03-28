from inference_service.schemas.inference import InferenceRequest


class MockInferenceAdapter:
    def describe(self):
        return {
            "engine_type": "mock",
            "model_name": "yolov13-rainfog",
            "model_version": "draft",
            "ready": True,
        }

    def detect(self, payload: InferenceRequest):
        return {
            "task_no": payload.task_no,
            "success": True,
            "engine_type": "mock",
            "engine_version": "0.1.0",
            "model_name": "yolov13-rainfog",
            "model_version": "draft",
            "duration_ms": 128,
            "result_image_path": payload.image_path.replace(".jpg", "_result.jpg"),
            "objects": [
                {
                    "class_id": 0,
                    "class_name": "car",
                    "confidence": 0.92,
                    "bbox": [120, 80, 360, 240],
                }
            ],
            "raw": {"mock": True, "scene": payload.scene},
        }
