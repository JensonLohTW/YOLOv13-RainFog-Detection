from django.db.models import Count

from apps.detection.models import DetectionObject, DetectionTask
from common.core.cache import cache


class DashboardService:
    CACHE_KEY = "dashboard:overview"

    def overview(self) -> dict:
        cached = cache.get_json(self.CACHE_KEY)
        if cached is not None:
            return cached

        payload = {
            "task_total": DetectionTask.objects.count(),
            "success_total": DetectionTask.objects.filter(status=DetectionTask.Status.SUCCESS).count(),
            "failed_total": DetectionTask.objects.filter(status=DetectionTask.Status.FAILED).count(),
            "processing_total": DetectionTask.objects.filter(status=DetectionTask.Status.PROCESSING).count(),
            "top_classes": list(
                DetectionObject.objects.values("class_name").annotate(count=Count("id")).order_by("-count")[:5]
            ),
            "cached": False,
        }
        cache.set_json(self.CACHE_KEY, payload)
        return payload

    def clear_overview_cache(self) -> None:
        cache.delete(self.CACHE_KEY)
