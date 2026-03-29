import httpx
from django.conf import settings


class InferenceServiceClient:
    def __init__(self) -> None:
        self.base_url = settings.INFERENCE_BASE_URL
        self.use_mock = settings.INFERENCE_USE_MOCK
        self.timeout = settings.INFERENCE_TIMEOUT

    def preview_mock_result(self):
        return {
            "engine": "mock" if self.use_mock else "remote",
            "base_url": self.base_url,
            "objects": [
                {
                    "class_name": "car",
                    "confidence": 0.92,
                    "bbox": [120, 80, 360, 240],
                }
            ],
        }

    def _local_mock_result(self, task_no: str, image_path: str, scene: str, preprocess: dict) -> dict:
        if image_path.endswith(".jpg"):
            result_image_path = image_path.replace(".jpg", "_result.jpg")
        elif image_path.endswith(".png"):
            result_image_path = image_path.replace(".png", "_result.png")
        else:
            result_image_path = f"{image_path}_result"

        return {
            "task_no": task_no,
            "success": True,
            "engine_type": "mock-fallback",
            "engine_version": "0.1.0",
            "model_name": "yolov13-rainfog",
            "model_version": "draft",
            "duration_ms": 64,
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
                "scene": scene,
                "fallback": True,
                "preprocess": preprocess,
            },
        }

    def _request(self, method: str, path: str, **kwargs) -> dict:
        response = httpx.request(
            method,
            f"{self.base_url}{path}",
            timeout=self.timeout,
            **kwargs,
        )
        response.raise_for_status()
        return response.json()

    def detect(
        self,
        task_no: str,
        image_path: str,
        confidence_threshold: float,
        iou_threshold: float,
        scene: str,
        preprocess_mode: str = "off",
        preprocess_profile: str = "",
        preprocess_algorithms: list[str] | None = None,
        preprocess_algorithm_params: dict | None = None,
        preprocess_enable_gamma: bool = False,
    ) -> dict:
        preprocess = {
            "mode": preprocess_mode,
            "profile": preprocess_profile,
            "algorithms": list(preprocess_algorithms or []),
            "algorithm_params": dict(preprocess_algorithm_params or {}),
            "enable_gamma": preprocess_enable_gamma,
        }
        payload = {
            "task_no": task_no,
            "image_path": image_path,
            "confidence_threshold": confidence_threshold,
            "iou_threshold": iou_threshold,
            "scene": scene,
            "preprocess_mode": preprocess_mode,
            "preprocess_profile": preprocess_profile,
            "preprocess_algorithms": list(preprocess_algorithms or []),
            "preprocess_algorithm_params": dict(preprocess_algorithm_params or {}),
            "preprocess_enable_gamma": preprocess_enable_gamma,
            "mock": self.use_mock,
        }
        try:
            return self._request("POST", "/internal/inference/detect", json=payload)
        except httpx.HTTPError:
            if self.use_mock:
                return self._local_mock_result(task_no, image_path, scene, preprocess)
            raise

    def get_runtime_summary(self) -> dict:
        # 這裡統一封裝 FastAPI 運行資訊，避免 Django 業務層直接處理細節。
        try:
            health = self._request("GET", "/internal/health")
            model = self._request("GET", "/internal/models/current")
            return {
                "health_status": health.get("status", "unknown"),
                "service": health.get("service", "fastapi-inference"),
                "model": model,
            }
        except httpx.HTTPError:
            return {
                "health_status": "degraded",
                "service": "fastapi-inference",
                "model": {
                    "engine_type": "mock-fallback" if self.use_mock else "unreachable",
                    "model_name": "yolov13-rainfog",
                    "model_version": "draft",
                    "ready": self.use_mock,
                    "note": "推理服務不可達，當前返回的是 Django 側兜底資訊。",
                },
            }
