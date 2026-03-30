from io import BytesIO
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APIClient

from apps.media.services import ImageAssetService


def build_test_image(name: str = "scene.jpg") -> SimpleUploadedFile:
    buffer = BytesIO()
    Image.new("RGB", (32, 32), color=(25, 50, 75)).save(buffer, format="JPEG")
    buffer.seek(0)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/jpeg")


def build_inference_response(task_no: str, scene: str, recognition_mode: str, runtime_options: dict) -> dict:
    return {
        "task_no": task_no,
        "success": True,
        "engine_type": "mock",
        "engine_version": "0.1.0",
        "model_name": "yolov13-rainfog",
        "model_version": str(runtime_options.get("model_profile", "draft")),
        "duration_ms": 42,
        "result_image_path": "/tmp/result.jpg",
        "objects": [
            {
                "class_id": 0,
                "class_name": "car",
                "confidence": 0.91,
                "bbox": [10, 20, 30, 40],
            }
        ],
        "raw": {
            "mock": True,
            "scene": scene,
            "recognition_mode": recognition_mode,
            "runtime_options": runtime_options,
        },
    }


@override_settings(
    DETECTION_DEFAULT_RECOGNITION_MODE="scene_default",
    DETECTION_DEFAULT_SCENE="rain_fog",
    DETECTION_SCENE_CONFIDENCE_THRESHOLD=0.35,
    DETECTION_SCENE_IOU_THRESHOLD=0.5,
    DETECTION_SCENE_PREPROCESS_MODE="auto",
    DETECTION_SCENE_PREPROCESS_PROFILE="scene_default",
    DETECTION_SCENE_PREPROCESS_ENABLE_GAMMA=True,
    DETECTION_SCENE_MODEL_PROFILE="scene_default",
    DETECTION_SCENE_IMAGE_SIZE=960,
    DETECTION_SCENE_ENABLE_AUGMENT=True,
)
class DetectionModeApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.image = ImageAssetService().upload(build_test_image())

    @patch("apps.detection.services.InferenceServiceClient.detect")
    def test_create_task_uses_default_scene_mode_when_mode_is_omitted(self, mocked_detect) -> None:
        mocked_detect.side_effect = lambda **kwargs: build_inference_response(
            kwargs["task_no"],
            kwargs["scene"],
            kwargs["recognition_mode"],
            kwargs["runtime_options"],
        )
        response = self.client.post("/api/v1/detection/tasks", {"image_id": self.image.id}, format="json")
        self.assertEqual(response.status_code, 201)
        data = response.json()["data"]
        self.assertEqual(data["recognition_mode"], "scene_default")
        self.assertEqual(data["weather_scene"], "rain_fog")
        self.assertEqual(data["confidence_threshold"], 0.35)
        self.assertEqual(data["iou_threshold"], 0.5)
        self.assertEqual(data["preprocess_mode"], "auto")
        self.assertEqual(data["runtime_options"]["model_profile"], "scene_default")
        self.assertEqual(data["runtime_options"]["image_size"], 960)
        kwargs = mocked_detect.call_args.kwargs
        self.assertEqual(kwargs["recognition_mode"], "scene_default")
        self.assertEqual(kwargs["scene"], "rain_fog")
        self.assertTrue(kwargs["runtime_options"]["augment"])

    @patch("apps.detection.services.InferenceServiceClient.detect")
    def test_create_task_can_switch_back_to_image_mode(self, mocked_detect) -> None:
        mocked_detect.side_effect = lambda **kwargs: build_inference_response(
            kwargs["task_no"],
            kwargs["scene"],
            kwargs["recognition_mode"],
            kwargs["runtime_options"],
        )
        response = self.client.post(
            "/api/v1/detection/tasks",
            {
                "image_id": self.image.id,
                "recognition_mode": "image",
                "weather_scene": "fog",
                "confidence_threshold": 0.6,
                "iou_threshold": 0.2,
                "preprocess_mode": "manual",
                "preprocess_profile": "detail_focus",
                "preprocess_enable_gamma": False,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()["data"]
        self.assertEqual(data["recognition_mode"], "image")
        self.assertEqual(data["weather_scene"], "fog")
        self.assertEqual(data["confidence_threshold"], 0.6)
        self.assertEqual(data["iou_threshold"], 0.2)
        self.assertEqual(data["preprocess_mode"], "manual")
        self.assertEqual(data["runtime_options"]["model_profile"], "image_standard")
        kwargs = mocked_detect.call_args.kwargs
        self.assertEqual(kwargs["recognition_mode"], "image")
        self.assertEqual(kwargs["scene"], "fog")
        self.assertFalse(kwargs["runtime_options"]["augment"])

    def test_create_task_rejects_unknown_recognition_mode(self) -> None:
        response = self.client.post(
            "/api/v1/detection/tasks",
            {"image_id": self.image.id, "recognition_mode": "invalid_mode"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("recognition_mode", response.json())
