from io import BytesIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image
from rest_framework.test import APIClient

from apps.audit.models import OperationLog
from apps.media.services import ImageAssetService
from apps.system.models import SystemConfigItem
from common.llm import LLMResponse

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


class DetectionExplanationApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = User.objects.create_user(username="tester", password="secret123", is_staff=True)
        self.client.force_authenticate(user=self.user)
        self.image = ImageAssetService().upload(build_test_image())

    @patch("apps.detection.services.InferenceServiceClient.detect")
    @patch("apps.detection.explanations.LLMClient.generate")
    def test_explanation_endpoint_returns_grounded_answer_for_task_no(self, mocked_generate, mocked_detect) -> None:
        mocked_detect.side_effect = lambda **kwargs: build_inference_response(
            kwargs["task_no"],
            kwargs["scene"],
            kwargs["recognition_mode"],
            kwargs["runtime_options"],
        )
        mocked_generate.return_value = LLMResponse(
            text="結論\n偵測到 car 與 person。\n\n依據\ncar 置信度 0.91，person 置信度 0.44。",
            provider="mock",
            model="mock-llm",
        )

        create_response = self.client.post("/api/v1/detection/tasks", {"image_id": self.image.id}, format="json")
        self.assertEqual(create_response.status_code, 201)
        task_no = create_response.json()["data"]["task_no"]

        response = self.client.post(
            "/api/v1/detection/explanations",
            {"task_no": task_no, "question": "這張圖有哪些目標？"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(payload["task_no"], task_no)
        self.assertIn("car", payload["answer"])
        self.assertEqual(payload["grounding"]["object_count"], 2)
        self.assertEqual(payload["grounding"]["class_summary"][0]["class_name"], "car")
        self.assertEqual(payload["llm"]["provider"], "mock")

    @patch("apps.detection.services.InferenceServiceClient.detect")
    @patch("apps.detection.explanations.LLMClient.generate")
    def test_explanation_endpoint_can_resolve_latest_task_by_image_id(self, mocked_generate, mocked_detect) -> None:
        mocked_detect.side_effect = lambda **kwargs: build_inference_response(
            kwargs["task_no"],
            kwargs["scene"],
            kwargs["recognition_mode"],
            kwargs["runtime_options"],
        )
        mocked_generate.return_value = LLMResponse(
            text="結論\n已解析最新一筆檢測結果。",
            provider="mock",
            model="mock-llm",
        )

        create_response = self.client.post("/api/v1/detection/tasks", {"image_id": self.image.id}, format="json")
        task_no = create_response.json()["data"]["task_no"]

        response = self.client.post(
            "/api/v1/detection/explanations",
            {"image_id": self.image.id, "question": "哪個框比較不確定？"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["task_no"], task_no)

    @patch.dict("os.environ", {"LLM_API_KEY": "super-secret-key"}, clear=False)
    def test_system_config_list_masks_sensitive_llm_api_key(self) -> None:
        response = self.client.get("/api/v1/system/configs")
        self.assertEqual(response.status_code, 200)
        items = response.json()["data"]["items"]
        api_key_item = next(item for item in items if item["config_key"] == "llm_api_key")

        self.assertEqual(api_key_item["config_value"], "")
        self.assertEqual(api_key_item["effective_source"], "env")
        self.assertTrue(api_key_item["has_effective_value"])
        self.assertNotIn("super-secret-key", api_key_item["display_value"])

    def test_system_config_update_redacts_api_key_in_operation_log(self) -> None:
        self.client.get("/api/v1/system/configs")
        item = SystemConfigItem.objects.get(config_key="llm_api_key")

        response = self.client.put(
            f"/api/v1/system/configs/{item.id}",
            {"config_value": "db-secret-value"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        log = OperationLog.objects.filter(path=f"/api/v1/system/configs/{item.id}").latest("created_at")
        self.assertIn('"config_value": "***"', log.request_body)
        self.assertNotIn("db-secret-value", log.request_body)
