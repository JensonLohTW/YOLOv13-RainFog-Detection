from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from typing import Any


class AnalyticsIntent:
    TASK_SUMMARY = "task_summary"
    TOP_CLASSES = "top_classes"
    TREND = "trend"
    SCENE_DISTRIBUTION = "scene_distribution"
    CLASS_DETAIL = "class_detail"
    AVG_CONFIDENCE_RANKING = "avg_confidence_ranking"

    ALL = {
        TASK_SUMMARY,
        TOP_CLASSES,
        TREND,
        SCENE_DISTRIBUTION,
        CLASS_DETAIL,
        AVG_CONFIDENCE_RANKING,
    }


@dataclass(frozen=True)
class AnalyticsQuerySpec:
    intent: str
    date_from: date
    date_to: date
    limit: int = 5
    class_name: str = ""
    metric: str = "count"
    group_by: str = "day"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["date_from"] = self.date_from.isoformat()
        payload["date_to"] = self.date_to.isoformat()
        return payload
