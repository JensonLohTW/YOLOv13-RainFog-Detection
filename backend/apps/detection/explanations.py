from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from django.db.models import Prefetch

from common.llm import (
    LLMClient,
    LLMConfigurationError,
    LLMProviderError,
    LLMRequestError,
    LLMTimeoutError,
)

from apps.system.services import SystemConfigService

from .models import DetectionObject, DetectionTask, InferenceRecord

DETECTION_EXPLANATION_SYSTEM_PROMPT = """你是 YOLOv13 RainFog Detection 的檢測結果解讀助手。

你只能根據提供的檢測結果上下文回答，不得捏造圖片中未被檢測結果支持的內容。

回答規則：
1. 使用繁體中文。
2. 先直接回答使用者問題，再補充依據。
3. 引用結果時，優先使用類別、數量、置信度、框大小、任務配置等可驗證欄位。
4. 若談論可能誤判原因，只能根據以下已知訊號推斷：低置信度、小目標、惡劣天氣場景、未檢測到目標、mock 推理。
5. 若證據不足，必須明確寫出「根據目前檢測結果無法確認」。
6. 請以以下格式回答：
   結論
   依據
   可能誤判原因
   建議下一步
"""


class DetectionExplanationError(Exception):
    def __init__(self, message: str, *, status: int = 400, code: int = 400) -> None:
        super().__init__(message)
        self.status = status
        self.code = code


class DetectionExplanationConfigError(DetectionExplanationError):
    def __init__(self, message: str) -> None:
        super().__init__(message, status=503, code=503)


@dataclass(frozen=True)
class DetectionExplanationRequest:
    question: str
    task_no: str = ""
    image_id: int | None = None


class DetectionGroundingService:
    def get_grounding(
        self,
        *,
        task_no: str = "",
        image_id: int | None = None,
    ) -> tuple[DetectionTask, dict[str, Any]]:
        task = self._resolve_task(task_no=task_no, image_id=image_id)
        record = task.inference_records.first()
        if record is None:
            raise DetectionExplanationError("找不到可用的推理結果，無法生成說明。", status=404, code=404)
        return task, self._build_grounding(task, record)

    def _resolve_task(self, *, task_no: str, image_id: int | None) -> DetectionTask:
        queryset = DetectionTask.objects.select_related("image").prefetch_related(
            Prefetch(
                "inference_records",
                queryset=InferenceRecord._default_manager.prefetch_related("objects"),
            )
        )

        if task_no:
            task = queryset.filter(task_no=task_no).first()
            if task is None:
                raise DetectionExplanationError("指定的任務不存在。", status=404, code=404)
            return task

        if image_id is None:
            raise DetectionExplanationError("請提供 task_no 或 image_id。")

        candidates = list(queryset.filter(image_id=image_id)[:20])
        if not candidates:
            raise DetectionExplanationError("指定的圖片不存在對應的檢測任務。", status=404, code=404)

        success_task = next(
            (
                item
                for item in candidates
                if item.status == DetectionTask.Status.SUCCESS and item.inference_records.first() is not None
            ),
            None,
        )
        if success_task is not None:
            return success_task

        fallback = next((item for item in candidates if item.inference_records.first() is not None), None)
        if fallback is None:
            raise DetectionExplanationError("指定圖片尚未產生可用的推理結果。", status=404, code=404)
        return fallback

    def _build_user_prompt(self, *, question: str, grounding: dict[str, Any]) -> str:
        return (
            "使用者問題：\n"
            f"{question.strip()}\n\n"
            "檢測結果上下文（JSON）：\n"
            f"{json.dumps(grounding, ensure_ascii=False, indent=2)}"
        )

    def _build_grounding(self, task: DetectionTask, record: InferenceRecord) -> dict[str, Any]:
        objects = [self._serialize_object(obj, task=task) for obj in record.objects.all()]
        class_summary = self._summarize_classes(objects)
        low_confidence_threshold = max(float(task.confidence_threshold), 0.5)
        lowest_confidence_objects = [
            item for item in sorted(objects, key=lambda value: value["confidence"])[:3] if objects
        ]
        small_objects = [item for item in objects if item["area_ratio"] is not None and item["area_ratio"] < 0.02]
        warnings = self._build_warnings(
            task=task,
            record=record,
            objects=objects,
            low_confidence_threshold=low_confidence_threshold,
            small_object_count=len(small_objects),
        )

        return {
            "task_no": task.task_no,
            "status": task.status,
            "recognition_mode": task.recognition_mode,
            "weather_scene": task.weather_scene,
            "thresholds": {
                "confidence": task.confidence_threshold,
                "iou": task.iou_threshold,
            },
            "image": {
                "id": task.image_id,
                "name": task.image.original_name,
                "width": task.image.width,
                "height": task.image.height,
            },
            "inference": {
                "engine_type": record.engine_type,
                "model_name": record.model_name,
                "model_version": record.model_version,
                "duration_ms": record.duration_ms,
                "object_count": record.object_count,
                "avg_confidence": record.avg_confidence,
                "is_mock": record.is_mock,
            },
            "object_count": len(objects),
            "class_summary": class_summary,
            "lowest_confidence_objects": lowest_confidence_objects,
            "small_object_count": len(small_objects),
            "warnings": warnings,
            "objects": objects[:20],
            "truncated_object_count": max(0, len(objects) - 20),
        }

    def _serialize_object(self, obj: DetectionObject, *, task: DetectionTask) -> dict[str, Any]:
        image_area = None
        if task.image.width and task.image.height:
            image_area = task.image.width * task.image.height
        bbox_area = obj.bbox_width * obj.bbox_height
        area_ratio = round(bbox_area / image_area, 4) if image_area else None
        return {
            "class_id": obj.class_id,
            "class_name": obj.class_name,
            "confidence": round(obj.confidence, 4),
            "bbox": [obj.bbox_x1, obj.bbox_y1, obj.bbox_x2, obj.bbox_y2],
            "bbox_width": obj.bbox_width,
            "bbox_height": obj.bbox_height,
            "area_ratio": area_ratio,
            "confidence_level": self._confidence_level(obj.confidence),
        }

    def _summarize_classes(self, objects: list[dict[str, Any]]) -> list[dict[str, Any]]:
        grouped: dict[str, dict[str, Any]] = defaultdict(lambda: {"count": 0, "confidences": []})
        for item in objects:
            entry = grouped[item["class_name"]]
            entry["count"] += 1
            entry["confidences"].append(item["confidence"])

        summary = []
        for class_name, values in grouped.items():
            confidences = values["confidences"]
            summary.append(
                {
                    "class_name": class_name,
                    "count": values["count"],
                    "avg_confidence": round(sum(confidences) / len(confidences), 4),
                    "max_confidence": round(max(confidences), 4),
                    "min_confidence": round(min(confidences), 4),
                }
            )
        return sorted(summary, key=lambda item: (-item["count"], -item["avg_confidence"], item["class_name"]))

    def _build_warnings(
        self,
        *,
        task: DetectionTask,
        record: InferenceRecord,
        objects: list[dict[str, Any]],
        low_confidence_threshold: float,
        small_object_count: int,
    ) -> list[str]:
        warnings: list[str] = []
        low_confidence_count = sum(1 for item in objects if item["confidence"] < low_confidence_threshold)

        if not objects:
            warnings.append("目前沒有檢測到任何目標，需留意漏檢或閾值過高的可能。")
        if low_confidence_count:
            warnings.append(f"有 {low_confidence_count} 個目標的置信度低於 {low_confidence_threshold:.2f}。")
        if small_object_count:
            warnings.append(f"有 {small_object_count} 個目標框面積占比小於 2%，可能受小目標影響。")
        if task.weather_scene in {
            DetectionTask.WeatherScene.RAIN,
            DetectionTask.WeatherScene.FOG,
            DetectionTask.WeatherScene.RAIN_FOG,
        }:
            warnings.append("任務場景屬於雨霧能見度受限環境，模型判讀可能更不穩定。")
        if record.is_mock:
            warnings.append("目前結果來自 mock 推理，僅適合流程驗證，不代表真實模型效果。")
        return warnings

    def _confidence_level(self, confidence: float) -> str:
        if confidence >= 0.8:
            return "high"
        if confidence >= 0.5:
            return "medium"
        return "low"


class DetectionExplanationService:
    def __init__(self) -> None:
        self.llm_client = LLMClient()
        self.system_config_service = SystemConfigService()
        self.grounding_service = DetectionGroundingService()

    def answer(self, request: DetectionExplanationRequest) -> dict[str, Any]:
        task, grounding = self.grounding_service.get_grounding(
            task_no=request.task_no,
            image_id=request.image_id,
        )
        llm_settings = self.system_config_service.get_llm_settings()
        system_prompt = DETECTION_EXPLANATION_SYSTEM_PROMPT
        user_prompt = (
            "使用者問題：\n"
            f"{request.question.strip()}\n\n"
            "檢測結果上下文（JSON）：\n"
            f"{json.dumps(grounding, ensure_ascii=False, indent=2)}"
        )

        try:
            response = self.llm_client.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                settings=llm_settings,
                metadata={
                    "agent_type": "detection_explanation",
                    "question": request.question,
                    "grounding": grounding,
                },
            )
        except LLMConfigurationError as exc:
            raise DetectionExplanationConfigError(str(exc)) from exc
        except LLMTimeoutError as exc:
            raise DetectionExplanationError(str(exc), status=504, code=504) from exc
        except (LLMRequestError, LLMProviderError) as exc:
            raise DetectionExplanationError(str(exc), status=502, code=502) from exc

        return {
            "task_no": task.task_no,
            "image_id": task.image_id,
            "question": request.question,
            "answer": response.text,
            "grounding": grounding,
            "llm": {
                "provider": response.provider,
                "model": response.model,
                "config_source": llm_settings.config_source,
                "api_key_source": llm_settings.api_key_source,
            },
        }
