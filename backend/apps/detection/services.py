from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.dashboard.services import DashboardService
from apps.media.models import ImageAsset
from integrations.inference.client import InferenceServiceClient

from .models import DetectionObject, DetectionTask, InferenceRecord
from .modes import RecognitionModeResolver


@dataclass
class DetectionRequest:
    image: ImageAsset
    recognition_mode: str | None = None
    weather_scene: str | None = None
    confidence_threshold: float | None = None
    iou_threshold: float | None = None
    preprocess_mode: str | None = None
    preprocess_profile: str | None = None
    preprocess_algorithms: list[str] | None = None
    preprocess_algorithm_params: dict[str, object] | None = None
    preprocess_enable_gamma: bool | None = None
    requested_by: Any = None


class DetectionTaskService:
    def __init__(self) -> None:
        self.client = InferenceServiceClient()
        self.dashboard_service = DashboardService()
        self.mode_resolver = RecognitionModeResolver()

    @transaction.atomic
    def create_and_run(self, request: DetectionRequest) -> DetectionTask:
        resolved = self.mode_resolver.resolve(
            recognition_mode=request.recognition_mode,
            weather_scene=request.weather_scene,
            confidence_threshold=request.confidence_threshold,
            iou_threshold=request.iou_threshold,
            preprocess_mode=request.preprocess_mode,
            preprocess_profile=request.preprocess_profile,
            preprocess_algorithms=request.preprocess_algorithms,
            preprocess_algorithm_params=request.preprocess_algorithm_params,
            preprocess_enable_gamma=request.preprocess_enable_gamma,
        )
        task = DetectionTask.objects.create(
            image=request.image,
            status=DetectionTask.Status.QUEUED,
            recognition_mode=resolved.recognition_mode,
            weather_scene=resolved.weather_scene,
            confidence_threshold=resolved.confidence_threshold,
            iou_threshold=resolved.iou_threshold,
            preprocess_mode=resolved.preprocess_mode,
            preprocess_profile=resolved.preprocess_profile,
            preprocess_algorithms=resolved.preprocess_algorithms,
            preprocess_algorithm_params=resolved.preprocess_algorithm_params,
            preprocess_enable_gamma=resolved.preprocess_enable_gamma,
            runtime_options=resolved.runtime_options,
            requested_by=request.requested_by if getattr(request.requested_by, "is_authenticated", False) else None,
        )
        return self._run_for_existing_task(task)

    def _run_inference(self, task: DetectionTask) -> dict:
        return self.client.detect(
            task_no=task.task_no,
            image_path=task.image.file.path,
            recognition_mode=task.recognition_mode,
            confidence_threshold=task.confidence_threshold,
            iou_threshold=task.iou_threshold,
            scene=task.weather_scene,
            preprocess_mode=task.preprocess_mode,
            preprocess_profile=task.preprocess_profile,
            preprocess_algorithms=task.preprocess_algorithms,
            preprocess_algorithm_params=task.preprocess_algorithm_params,
            preprocess_enable_gamma=task.preprocess_enable_gamma,
            runtime_options=task.runtime_options,
        )

    def _run_for_existing_task(self, task: DetectionTask) -> DetectionTask:
        task.status = DetectionTask.Status.PROCESSING
        task.started_at = timezone.now()
        task.finished_at = None
        task.error_message = ""
        task.save(update_fields=["status", "started_at", "finished_at", "error_message", "updated_at"])
        inference_response = self._run_inference(task)
        return self._persist_result(task, inference_response)

    @transaction.atomic
    def retry(self, task: DetectionTask) -> DetectionTask:
        return self._run_for_existing_task(task)

    def _persist_result(self, task: DetectionTask, inference_response: dict) -> DetectionTask:
        objects = inference_response.get("objects", [])
        confidences = [obj.get("confidence", 0.0) for obj in objects]
        record = InferenceRecord._default_manager.create(
            task=task,
            engine_type=inference_response.get("engine_type", "unknown"),
            engine_version=inference_response.get("engine_version", ""),
            model_name=inference_response.get("model_name", ""),
            model_version=inference_response.get("model_version", ""),
            request_payload={
                "task_no": task.task_no,
                "image_path": task.image.file.path,
                "recognition_mode": task.recognition_mode,
                "weather_scene": task.weather_scene,
                "confidence_threshold": task.confidence_threshold,
                "iou_threshold": task.iou_threshold,
                "preprocess_mode": task.preprocess_mode,
                "preprocess_profile": task.preprocess_profile,
                "preprocess_algorithms": task.preprocess_algorithms,
                "preprocess_algorithm_params": task.preprocess_algorithm_params,
                "preprocess_enable_gamma": task.preprocess_enable_gamma,
                "runtime_options": task.runtime_options,
            },
            response_payload=inference_response,
            result_image_path=inference_response.get("result_image_path", ""),
            result_image_url="",
            object_count=len(objects),
            avg_confidence=(sum(confidences) / len(confidences)) if confidences else None,
            duration_ms=inference_response.get("duration_ms", 0),
            is_mock=inference_response.get("raw", {}).get("mock", False),
        )
        for obj in objects:
            x1, y1, x2, y2 = obj.get("bbox", [0, 0, 0, 0])
            DetectionObject.objects.create(
                record=record,
                class_name=obj.get("class_name", "unknown"),
                class_id=obj.get("class_id", -1),
                confidence=obj.get("confidence", 0.0),
                bbox_x1=x1,
                bbox_y1=y1,
                bbox_x2=x2,
                bbox_y2=y2,
                bbox_width=max(0, x2 - x1),
                bbox_height=max(0, y2 - y1),
                area_ratio=None,
            )
        task.status = DetectionTask.Status.SUCCESS if inference_response.get("success") else DetectionTask.Status.FAILED
        task.finished_at = timezone.now()
        task.error_message = "" if inference_response.get("success") else "Inference failed"
        task.save(update_fields=["status", "finished_at", "error_message", "updated_at"])
        self.dashboard_service.clear_overview_cache()
        return task
