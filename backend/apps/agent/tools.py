from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, time as dt_time, timedelta
from typing import Any

from django.db.models import Avg, Count, DateField, F, Max, Min, Q
from django.db.models.expressions import RawSQL
from django.db.models.functions import Cast, TruncDate
from django.utils import timezone

from apps.dashboard.services import DashboardService
from apps.detection.explanations import DetectionExplanationError, DetectionGroundingService
from apps.detection.models import DetectionObject, DetectionTask
from apps.system.services import SystemConfigService
from common.llm import LLMClient

from .analytics_dsl import AnalyticsIntent, AnalyticsQuerySpec
from .contracts import ToolExecutionTrace
from .prompts import ANALYTICS_AGENT_SYSTEM_PROMPT, DETECTION_AGENT_SYSTEM_PROMPT

CLASS_NAME_PATTERNS = [
    r"類別[是為:]\s*([A-Za-z0-9_\-\u4e00-\u9fff]+)",
    r"\b([A-Za-z0-9_\-]+)\s*類別",
    r"[\"'「](.+?)[\"'」]\s*類別",
]


class AgentToolError(Exception):
    def __init__(self, message: str, *, code: str = "tool_error", status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.status = status


@dataclass(frozen=True)
class ToolResult:
    payload: dict[str, Any]
    trace: ToolExecutionTrace


class DetectionGroundingTool:
    TOOL_NAME = "detection_grounding"

    def __init__(self) -> None:
        self.service = DetectionGroundingService()

    def execute(self, *, task_no: str = "", image_id: int | None = None) -> ToolResult:
        started = time.perf_counter()
        try:
            task, grounding = self.service.get_grounding(task_no=task_no, image_id=image_id)
        except DetectionExplanationError as exc:
            raise AgentToolError(str(exc), code="grounding_error", status=exc.status) from exc
        latency_ms = int((time.perf_counter() - started) * 1000)
        return ToolResult(
            payload={
                "task_no": task.task_no,
                "image_id": task.image_id,
                "grounding": grounding,
            },
            trace=ToolExecutionTrace(
                tool_name=self.TOOL_NAME,
                latency_ms=latency_ms,
                payload={"task_no": task.task_no, "object_count": grounding.get("object_count", 0)},
            ),
        )


class AnalyticsIntentTool:
    TOOL_NAME = "analytics_intent_parser"

    def execute(self, *, question: str) -> ToolResult:
        started = time.perf_counter()
        spec = self._build_spec(question)
        latency_ms = int((time.perf_counter() - started) * 1000)
        return ToolResult(
            payload=spec.to_dict(),
            trace=ToolExecutionTrace(
                tool_name=self.TOOL_NAME,
                latency_ms=latency_ms,
                payload={
                    "intent": spec.intent,
                    "date_from": spec.date_from.isoformat(),
                    "date_to": spec.date_to.isoformat(),
                    "limit": spec.limit,
                    "class_name": spec.class_name,
                    "metric": spec.metric,
                },
            ),
        )

    def _build_spec(self, question: str) -> AnalyticsQuerySpec:
        question = question.strip()
        question_lower = question.lower()
        date_from, date_to = self._extract_date_range(question)
        if date_from is None or date_to is None:
            days = self._extract_recent_days(question)
            date_to = timezone.localdate()
            date_from = date_to - timedelta(days=days - 1)

        class_name = self._extract_class_name(question)
        limit = self._extract_limit(question_lower)
        metric = self._extract_metric(question)
        intent = self._detect_intent(question, class_name=class_name)

        return AnalyticsQuerySpec(
            intent=intent,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            class_name=class_name,
            metric=metric,
            group_by="day",
        )

    def _detect_intent(self, question: str, *, class_name: str) -> str:
        question_lower = question.lower()

        if "場景" in question and any(keyword in question for keyword in ["分布", "比例", "最多", "占比"]):
            return AnalyticsIntent.SCENE_DISTRIBUTION
        if class_name and any(keyword in question for keyword in ["多少", "幾次", "幾個", "置信度", "信心", "表現"]):
            return AnalyticsIntent.CLASS_DETAIL
        if class_name and any(keyword in question for keyword in ["趨勢", "變化", "每日", "每天"]):
            return AnalyticsIntent.CLASS_DETAIL
        if "平均置信度" in question or "平均信心" in question:
            return AnalyticsIntent.AVG_CONFIDENCE_RANKING
        if any(keyword in question_lower for keyword in ["趨勢", "變化", "每日", "每天"]):
            return AnalyticsIntent.TREND
        if any(keyword in question_lower for keyword in ["最多", "熱門", "top", "最高"]):
            return AnalyticsIntent.TOP_CLASSES
        return AnalyticsIntent.TASK_SUMMARY

    def _extract_metric(self, question: str) -> str:
        if "平均置信度" in question or "平均信心" in question:
            return "avg_confidence"
        if "成功率" in question:
            return "success_rate"
        if "失敗率" in question:
            return "failure_rate"
        return "count"

    def _extract_recent_days(self, question: str) -> int:
        match = re.search(r"(最近|近)\s*(\d+)\s*天", question)
        if match:
            return max(1, min(int(match.group(2)), 90))
        if "最近一週" in question or "近一週" in question:
            return 7
        if "最近兩週" in question or "近兩週" in question:
            return 14
        if "最近一個月" in question or "近一個月" in question:
            return 30
        return 7

    def _extract_date_range(self, question: str):  # noqa: ANN001
        matches = re.findall(r"(20\d{2}-\d{2}-\d{2})", question)
        if len(matches) >= 2:
            start = datetime.fromisoformat(matches[0]).date()
            end = datetime.fromisoformat(matches[1]).date()
            if start > end:
                start, end = end, start
            return start, end
        return None, None

    def _extract_limit(self, question: str) -> int:
        match = re.search(r"(top|前)\s*(\d+)", question)
        if match:
            return max(1, min(int(match.group(2)), 10))
        return 5

    def _extract_class_name(self, question: str) -> str:
        for pattern in CLASS_NAME_PATTERNS:
            match = re.search(pattern, question)
            if match:
                return match.group(1).strip("「」\"' ")
        return ""


class AnalyticsQueryTool:
    TOOL_NAME = "analytics_query"

    def __init__(self) -> None:
        self.dashboard_service = DashboardService()

    def execute(self, *, spec: dict[str, Any]) -> ToolResult:
        started = time.perf_counter()
        query_spec = self._build_query_spec(spec)
        task_queryset = self._build_task_queryset(query_spec)
        object_queryset = self._build_object_queryset(query_spec)

        status_summary = self._build_status_summary(task_queryset)
        top_classes = self._build_top_classes(object_queryset, limit=query_spec.limit)
        trend = self._build_daily_trend(task_queryset)
        scene_distribution = self._build_scene_distribution(task_queryset)
        avg_confidence_ranking = self._build_avg_confidence_ranking(object_queryset, limit=query_spec.limit)
        class_detail = self._build_class_detail(
            object_queryset=object_queryset,
            query_spec=query_spec,
        )
        result = self._build_result_payload(
            query_spec=query_spec,
            status_summary=status_summary,
            top_classes=top_classes,
            trend=trend,
            scene_distribution=scene_distribution,
            avg_confidence_ranking=avg_confidence_ranking,
            class_detail=class_detail,
        )

        payload = {
            "intent": query_spec.intent,
            "dsl": query_spec.to_dict(),
            "window": {
                "date_from": query_spec.date_from.isoformat(),
                "date_to": query_spec.date_to.isoformat(),
            },
            "status_summary": status_summary,
            "result": result,
            "top_classes": top_classes,
            "daily_trend": trend,
            "scene_distribution": scene_distribution,
            "avg_confidence_ranking": avg_confidence_ranking,
            "class_detail": class_detail,
            "available_intents": sorted(AnalyticsIntent.ALL),
            "dashboard_overview": self.dashboard_service.overview(),
        }
        latency_ms = int((time.perf_counter() - started) * 1000)
        return ToolResult(
            payload=payload,
            trace=ToolExecutionTrace(
                tool_name=self.TOOL_NAME,
                latency_ms=latency_ms,
                payload={
                    "intent": query_spec.intent,
                    "window": payload["window"],
                    "task_total": status_summary["task_total"],
                    "class_name": query_spec.class_name,
                },
            ),
        )

    def _build_query_spec(self, spec: dict[str, Any]) -> AnalyticsQuerySpec:
        intent = str(spec.get("intent") or "").strip()
        if intent not in AnalyticsIntent.ALL:
            raise AgentToolError(f"不支援的 analytics intent：{intent}", code="unsupported_intent")
        return AnalyticsQuerySpec(
            intent=intent,
            date_from=datetime.fromisoformat(spec["date_from"]).date(),
            date_to=datetime.fromisoformat(spec["date_to"]).date(),
            limit=max(1, min(int(spec.get("limit", 5)), 10)),
            class_name=str(spec.get("class_name") or "").strip(),
            metric=str(spec.get("metric") or "count").strip(),
            group_by=str(spec.get("group_by") or "day").strip(),
        )

    def _build_task_queryset(self, query_spec: AnalyticsQuerySpec):
        tz = timezone.get_current_timezone()
        start_dt = timezone.make_aware(datetime.combine(query_spec.date_from, dt_time.min), tz)
        end_dt = timezone.make_aware(datetime.combine(query_spec.date_to + timedelta(days=1), dt_time.min), tz)
        return DetectionTask.objects.filter(
            created_at__gte=start_dt,
            created_at__lt=end_dt,
        )

    def _build_object_queryset(self, query_spec: AnalyticsQuerySpec):
        tz = timezone.get_current_timezone()
        start_dt = timezone.make_aware(datetime.combine(query_spec.date_from, dt_time.min), tz)
        end_dt = timezone.make_aware(datetime.combine(query_spec.date_to + timedelta(days=1), dt_time.min), tz)
        queryset = DetectionObject.objects.filter(
            record__task__created_at__gte=start_dt,
            record__task__created_at__lt=end_dt,
        )
        if query_spec.class_name:
            queryset = queryset.filter(class_name__iexact=query_spec.class_name)
        return queryset

    def _build_status_summary(self, task_queryset) -> dict[str, Any]:  # noqa: ANN001
        task_total = task_queryset.count()
        success_total = task_queryset.filter(status=DetectionTask.Status.SUCCESS).count()
        failed_total = task_queryset.filter(status=DetectionTask.Status.FAILED).count()
        processing_total = task_queryset.filter(
            status__in=[DetectionTask.Status.PROCESSING, DetectionTask.Status.QUEUED]
        ).count()
        success_rate = round(success_total / task_total, 4) if task_total else 0.0
        failure_rate = round(failed_total / task_total, 4) if task_total else 0.0
        return {
            "task_total": task_total,
            "success_total": success_total,
            "failed_total": failed_total,
            "processing_total": processing_total,
            "success_rate": success_rate,
            "failure_rate": failure_rate,
        }

    def _build_top_classes(self, object_queryset, *, limit: int) -> list[dict[str, Any]]:  # noqa: ANN001
        rows = (
            object_queryset.values("class_name")
            .annotate(count=Count("id"), avg_confidence=Avg("confidence"))
            .order_by("-count", "-avg_confidence")[:limit]
        )
        return [
            {
                "class_name": item["class_name"],
                "count": item["count"],
                "avg_confidence": round(float(item["avg_confidence"] or 0.0), 4),
            }
            for item in rows
        ]

    def _build_avg_confidence_ranking(self, object_queryset, *, limit: int) -> list[dict[str, Any]]:  # noqa: ANN001
        rows = (
            object_queryset.values("class_name")
            .annotate(
                count=Count("id"),
                avg_confidence=Avg("confidence"),
                max_confidence=Max("confidence"),
                min_confidence=Min("confidence"),
            )
            .order_by("-avg_confidence", "-count")[:limit]
        )
        return [
            {
                "class_name": item["class_name"],
                "count": item["count"],
                "avg_confidence": round(float(item["avg_confidence"] or 0.0), 4),
                "max_confidence": round(float(item["max_confidence"] or 0.0), 4),
                "min_confidence": round(float(item["min_confidence"] or 0.0), 4),
            }
            for item in rows
        ]

    def _build_daily_trend(self, task_queryset) -> list[dict[str, Any]]:  # noqa: ANN001
        rows = (
            task_queryset.annotate(day=RawSQL("DATE(created_at)", [], output_field=DateField()))
            .values("day")
            .annotate(
                task_total=Count("id"),
                success_total=Count("id", filter=Q(status=DetectionTask.Status.SUCCESS)),
                failed_total=Count("id", filter=Q(status=DetectionTask.Status.FAILED)),
            )
            .order_by("day")
        )
        return [
            {
                "day": item["day"].isoformat(),
                "task_total": item["task_total"],
                "success_total": item["success_total"],
                "failed_total": item["failed_total"],
            }
            for item in rows
        ]

    def _build_scene_distribution(self, task_queryset) -> list[dict[str, Any]]:  # noqa: ANN001
        rows = (
            task_queryset.values("weather_scene")
            .annotate(count=Count("id"))
            .order_by("-count", "weather_scene")
        )
        total = sum(item["count"] for item in rows)
        return [
            {
                "weather_scene": item["weather_scene"],
                "count": item["count"],
                "ratio": round(item["count"] / total, 4) if total else 0.0,
            }
            for item in rows
        ]

    def _build_class_detail(
        self,
        *,
        object_queryset,
        query_spec: AnalyticsQuerySpec,
    ) -> dict[str, Any] | None:  # noqa: ANN001
        if not query_spec.class_name:
            return None

        summary = object_queryset.aggregate(
            count=Count("id"),
            avg_confidence=Avg("confidence"),
            max_confidence=Max("confidence"),
            min_confidence=Min("confidence"),
        )
        if not summary["count"]:
            return {
                "class_name": query_spec.class_name,
                "count": 0,
                "avg_confidence": 0.0,
                "max_confidence": 0.0,
                "min_confidence": 0.0,
                "daily_trend": [],
                "scene_distribution": [],
            }

        trend_rows = (
            object_queryset.annotate(day=Cast(F("record__task__created_at"), DateField()))
            .values("day")
            .annotate(count=Count("id"), avg_confidence=Avg("confidence"))
            .order_by("day")
        )
        scene_rows = (
            object_queryset.values("record__task__weather_scene")
            .annotate(count=Count("id"))
            .order_by("-count", "record__task__weather_scene")
        )
        return {
            "class_name": query_spec.class_name,
            "count": summary["count"],
            "avg_confidence": round(float(summary["avg_confidence"] or 0.0), 4),
            "max_confidence": round(float(summary["max_confidence"] or 0.0), 4),
            "min_confidence": round(float(summary["min_confidence"] or 0.0), 4),
            "daily_trend": [
                {
                    "day": item["day"].isoformat(),
                    "count": item["count"],
                    "avg_confidence": round(float(item["avg_confidence"] or 0.0), 4),
                }
                for item in trend_rows
            ],
            "scene_distribution": [
                {
                    "weather_scene": item["record__task__weather_scene"],
                    "count": item["count"],
                }
                for item in scene_rows
            ],
        }

    def _build_result_payload(
        self,
        *,
        query_spec: AnalyticsQuerySpec,
        status_summary: dict[str, Any],
        top_classes: list[dict[str, Any]],
        trend: list[dict[str, Any]],
        scene_distribution: list[dict[str, Any]],
        avg_confidence_ranking: list[dict[str, Any]],
        class_detail: dict[str, Any] | None,
    ) -> dict[str, Any]:
        if query_spec.intent == AnalyticsIntent.TOP_CLASSES:
            return {"items": top_classes, "metric": query_spec.metric}
        if query_spec.intent == AnalyticsIntent.TREND:
            return {"series": trend, "metric": query_spec.metric}
        if query_spec.intent == AnalyticsIntent.SCENE_DISTRIBUTION:
            return {"items": scene_distribution}
        if query_spec.intent == AnalyticsIntent.CLASS_DETAIL:
            return class_detail or {
                "class_name": query_spec.class_name,
                "count": 0,
                "avg_confidence": 0.0,
                "max_confidence": 0.0,
                "min_confidence": 0.0,
                "daily_trend": [],
                "scene_distribution": [],
            }
        if query_spec.intent == AnalyticsIntent.AVG_CONFIDENCE_RANKING:
            return {"items": avg_confidence_ranking, "metric": "avg_confidence"}
        return status_summary


class LLMAnswerTool:
    TOOL_NAME = "llm_answer_renderer"

    def __init__(self) -> None:
        self.llm_client = LLMClient()
        self.system_config_service = SystemConfigService()

    def execute(
        self,
        *,
        agent_type: str,
        question: str,
        grounding: dict[str, Any],
    ) -> ToolResult:
        started = time.perf_counter()
        llm_settings = self.system_config_service.get_llm_settings()
        system_prompt = self._get_system_prompt(agent_type)
        user_prompt = (
            "使用者問題：\n"
            f"{question.strip()}\n\n"
            "上下文（JSON）：\n"
            f"{json.dumps(grounding, ensure_ascii=False, indent=2)}"
        )
        response = self.llm_client.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            settings=llm_settings,
            metadata={
                "agent_type": agent_type,
                "question": question,
                "grounding": grounding,
            },
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        return ToolResult(
            payload={
                "answer": response.text,
                "llm": {
                    "provider": response.provider,
                    "model": response.model,
                    "config_source": llm_settings.config_source,
                    "api_key_source": llm_settings.api_key_source,
                },
            },
            trace=ToolExecutionTrace(
                tool_name=self.TOOL_NAME,
                latency_ms=latency_ms,
                payload={"provider": response.provider, "model": response.model},
            ),
        )

    def _get_system_prompt(self, agent_type: str) -> str:
        if agent_type == "analytics_qa":
            return ANALYTICS_AGENT_SYSTEM_PROMPT
        return DETECTION_AGENT_SYSTEM_PROMPT
