from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from django.db.models import Avg, Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.dashboard.services import DashboardService
from apps.detection.explanations import DetectionGroundingService
from apps.detection.models import DetectionObject, DetectionTask
from apps.system.services import SystemConfigService
from common.llm import LLMClient

from .contracts import ToolExecutionTrace
from .prompts import ANALYTICS_AGENT_SYSTEM_PROMPT, DETECTION_AGENT_SYSTEM_PROMPT


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
        task, grounding = self.service.get_grounding(task_no=task_no, image_id=image_id)
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
            payload=spec,
            trace=ToolExecutionTrace(
                tool_name=self.TOOL_NAME,
                latency_ms=latency_ms,
                payload={
                    "intent": spec["intent"],
                    "date_from": spec["date_from"],
                    "date_to": spec["date_to"],
                    "limit": spec["limit"],
                },
            ),
        )

    def _build_spec(self, question: str) -> dict[str, Any]:
        date_from, date_to = self._extract_date_range(question)
        if date_from is None or date_to is None:
            days = self._extract_recent_days(question)
            date_to = timezone.localdate()
            date_from = date_to - timedelta(days=days - 1)

        question_lower = question.lower()
        if any(keyword in question_lower for keyword in ["趨勢", "變化", "每日", "每天"]):
            intent = "trend"
        elif any(keyword in question_lower for keyword in ["最多", "熱門", "top", "最高"]):
            intent = "top_classes"
        else:
            intent = "task_summary"

        limit = self._extract_limit(question_lower)
        return {
            "intent": intent,
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
            "limit": limit,
        }

    def _extract_recent_days(self, question: str) -> int:
        match = re.search(r"(最近|近)\s*(\d+)\s*天", question)
        if match:
            return max(1, min(int(match.group(2)), 90))
        if "最近一週" in question or "近一週" in question:
            return 7
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


class AnalyticsQueryTool:
    TOOL_NAME = "analytics_query"

    def __init__(self) -> None:
        self.dashboard_service = DashboardService()

    def execute(self, *, spec: dict[str, Any]) -> ToolResult:
        started = time.perf_counter()
        date_from = datetime.fromisoformat(spec["date_from"]).date()
        date_to = datetime.fromisoformat(spec["date_to"]).date()
        task_filters = {"created_at__date__gte": date_from, "created_at__date__lte": date_to}

        task_queryset = DetectionTask.objects.filter(**task_filters)
        object_queryset = DetectionObject.objects.filter(
            record__task__created_at__date__gte=date_from,
            record__task__created_at__date__lte=date_to,
        )
        top_classes = list(
            object_queryset.values("class_name")
            .annotate(count=Count("id"), avg_confidence=Avg("confidence"))
            .order_by("-count", "-avg_confidence")[: spec["limit"]]
        )
        status_summary = {
            "task_total": task_queryset.count(),
            "success_total": task_queryset.filter(status=DetectionTask.Status.SUCCESS).count(),
            "failed_total": task_queryset.filter(status=DetectionTask.Status.FAILED).count(),
            "processing_total": task_queryset.filter(
                status__in=[DetectionTask.Status.PROCESSING, DetectionTask.Status.QUEUED]
            ).count(),
        }
        trend = list(
            task_queryset.annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(
                task_total=Count("id"),
                success_total=Count("id", filter=Q(status=DetectionTask.Status.SUCCESS)),
                failed_total=Count("id", filter=Q(status=DetectionTask.Status.FAILED)),
            )
            .order_by("day")
        )
        payload = {
            "intent": spec["intent"],
            "window": {
                "date_from": spec["date_from"],
                "date_to": spec["date_to"],
            },
            "status_summary": status_summary,
            "top_classes": [
                {
                    "class_name": item["class_name"],
                    "count": item["count"],
                    "avg_confidence": round(float(item["avg_confidence"] or 0.0), 4),
                }
                for item in top_classes
            ],
            "daily_trend": [
                {
                    "day": item["day"].isoformat(),
                    "task_total": item["task_total"],
                    "success_total": item["success_total"],
                    "failed_total": item["failed_total"],
                }
                for item in trend
            ],
            "dashboard_overview": self.dashboard_service.overview(),
        }
        latency_ms = int((time.perf_counter() - started) * 1000)
        return ToolResult(
            payload=payload,
            trace=ToolExecutionTrace(
                tool_name=self.TOOL_NAME,
                latency_ms=latency_ms,
                payload={
                    "intent": spec["intent"],
                    "window": payload["window"],
                    "task_total": status_summary["task_total"],
                },
            ),
        )


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
