from io import BytesIO
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from apps.detection.models import DetectionObject, DetectionTask, InferenceRecord
from apps.media.services import ImageAssetService
from apps.agent.tools import AnalyticsIntentTool

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
        self.intent_tool = AnalyticsIntentTool()

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

    def test_analytics_intent_tool_supports_scene_distribution(self) -> None:
        result = self.intent_tool.execute(question="最近 14 天各場景分布如何？")
        self.assertEqual(result.payload["intent"], "scene_distribution")
        self.assertEqual(result.payload["date_to"], timezone.localdate().isoformat())

    def test_analytics_intent_tool_supports_class_detail(self) -> None:
        result = self.intent_tool.execute(question="最近 7 天 car 類別平均置信度如何？")
        self.assertEqual(result.payload["intent"], "class_detail")
        self.assertEqual(result.payload["class_name"], "car")
        self.assertEqual(result.payload["metric"], "avg_confidence")

    def test_agent_ask_supports_scene_distribution_qa(self) -> None:
        self._seed_detection_task(weather_scene="fog", class_name="car", confidence=0.91, days_ago=1)
        self._seed_detection_task(weather_scene="fog", class_name="bus", confidence=0.83, days_ago=2)
        self._seed_detection_task(weather_scene="rain", class_name="car", confidence=0.72, days_ago=3)

        response = self.client.post(
            "/api/v1/agent/ask",
            {
                "agent_type": "analytics_qa",
                "question": "最近 7 天各場景分布如何？",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(payload["grounding"]["intent"], "scene_distribution")
        self.assertEqual(payload["grounding"]["result"]["items"][0]["weather_scene"], "fog")

    def test_agent_ask_supports_class_detail_qa(self) -> None:
        self._seed_detection_task(weather_scene="fog", class_name="car", confidence=0.91, days_ago=1)
        self._seed_detection_task(weather_scene="rain", class_name="car", confidence=0.61, days_ago=2)
        self._seed_detection_task(weather_scene="rain", class_name="bus", confidence=0.88, days_ago=2)

        response = self.client.post(
            "/api/v1/agent/ask",
            {
                "agent_type": "analytics_qa",
                "question": "最近 7 天 car 類別表現如何？",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(payload["grounding"]["intent"], "class_detail")
        self.assertEqual(payload["grounding"]["result"]["class_name"], "car")
        self.assertEqual(payload["grounding"]["result"]["count"], 2)

    def _seed_detection_task(
        self,
        *,
        weather_scene: str,
        class_name: str,
        confidence: float,
        days_ago: int,
    ) -> DetectionTask:
        task = DetectionTask.objects.create(
            image=self.image,
            status=DetectionTask.Status.SUCCESS,
            recognition_mode=DetectionTask.RecognitionMode.IMAGE,
            weather_scene=weather_scene,
            confidence_threshold=0.25,
            iou_threshold=0.45,
        )
        created_at = timezone.now() - timedelta(days=days_ago)
        DetectionTask.objects.filter(pk=task.pk).update(created_at=created_at, updated_at=created_at)
        task.refresh_from_db()

        record = InferenceRecord.objects.create(
            task=task,
            engine_type="mock",
            model_name="yolov13-rainfog",
            model_version="test",
            object_count=1,
            avg_confidence=confidence,
            duration_ms=20,
            is_mock=True,
        )
        InferenceRecord.objects.filter(pk=record.pk).update(created_at=created_at)
        record.refresh_from_db()

        DetectionObject.objects.create(
            record=record,
            class_name=class_name,
            class_id=0,
            confidence=confidence,
            bbox_x1=10,
            bbox_y1=10,
            bbox_x2=50,
            bbox_y2=50,
            bbox_width=40,
            bbox_height=40,
            area_ratio=0.15,
        )
        return task
