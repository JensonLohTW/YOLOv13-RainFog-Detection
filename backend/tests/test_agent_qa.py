from io import BytesIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image
from rest_framework.test import APIClient

from apps.media.services import ImageAssetService

User = get_user_model()


def build_test_image(name: str = "scene.jpg") -> SimpleUploadedFile:
    buffer = BytesIO()
    Image.new("RGB", (120, 80), color=(25, 50, 75)).save(buffer, format="JPEG")
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
                "bbox": [10, 20, 70, 60],
            },
            {
                "class_id": 1,
                "class_name": "person",
                "confidence": 0.44,
                "bbox": [80, 10, 95, 40],
            },
        ],
        "raw": {
            "mock": True,
            "scene": scene,
            "recognition_mode": recognition_mode,
            "runtime_options": runtime_options,
        },
    }


class AgentApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = User.objects.create_user(username="agent-tester", password="secret123", is_staff=True)
        self.client.force_authenticate(user=self.user)
        self.image = ImageAssetService().upload(build_test_image())

    @patch("apps.detection.services.InferenceServiceClient.detect")
    def test_agent_ask_supports_detection_explanation(self, mocked_detect) -> None:
        mocked_detect.side_effect = lambda **kwargs: build_inference_response(
            kwargs["task_no"],
            kwargs["scene"],
            kwargs["recognition_mode"],
            kwargs["runtime_options"],
        )

        create_response = self.client.post("/api/v1/detection/tasks", {"image_id": self.image.id}, format="json")
        self.assertEqual(create_response.status_code, 201)
        task_no = create_response.json()["data"]["task_no"]

        response = self.client.post(
            "/api/v1/agent/ask",
            {
                "agent_type": "detection_explanation",
                "task_no": task_no,
                "question": "這張圖有哪些偵測結果？",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(payload["agent_type"], "detection_explanation")
        self.assertEqual(payload["task_no"], task_no)
        self.assertGreaterEqual(len(payload["trace"]), 2)

    def test_agent_ask_supports_analytics_qa(self) -> None:
        response = self.client.post(
            "/api/v1/agent/ask",
            {
                "agent_type": "analytics_qa",
                "question": "最近 7 天哪些類別出現最多？",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(payload["agent_type"], "analytics_qa")
        self.assertIn("grounding", payload)
        self.assertEqual(payload["grounding"]["intent"], "top_classes")
        self.assertGreaterEqual(len(payload["trace"]), 3)
