from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

from apps.media.models import ImageAsset

User = get_user_model()


def generate_task_no() -> str:
    return f"DT{timezone.now():%Y%m%d%H%M%S}{uuid4().hex[:6].upper()}"


class DetectionTask(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        QUEUED = "QUEUED", "Queued"
        PROCESSING = "PROCESSING", "Processing"
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"
        CANCELED = "CANCELED", "Canceled"

    class TriggerMode(models.TextChoices):
        MANUAL = "manual", "Manual"
        BATCH = "batch", "Batch"
        API = "api", "API"

    class SourceType(models.TextChoices):
        IMAGE_UPLOAD = "image_upload", "Image Upload"
        HISTORICAL_REPLAY = "historical_replay", "Historical Replay"

    class RecognitionMode(models.TextChoices):
        SCENE_DEFAULT = "scene_default", "Scene Default"
        IMAGE = "image", "Image"

    class WeatherScene(models.TextChoices):
        RAIN = "rain", "Rain"
        FOG = "fog", "Fog"
        RAIN_FOG = "rain_fog", "Rain + Fog"
        UNKNOWN = "unknown", "Unknown"

    task_no = models.CharField(max_length=32, unique=True, default=generate_task_no)
    image = models.ForeignKey(ImageAsset, on_delete=models.PROTECT, related_name="detection_tasks")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    trigger_mode = models.CharField(max_length=16, choices=TriggerMode.choices, default=TriggerMode.MANUAL)
    source_type = models.CharField(max_length=32, choices=SourceType.choices, default=SourceType.IMAGE_UPLOAD)
    recognition_mode = models.CharField(
        max_length=32,
        choices=RecognitionMode.choices,
        default=RecognitionMode.SCENE_DEFAULT,
    )
    weather_scene = models.CharField(max_length=16, choices=WeatherScene.choices, default=WeatherScene.UNKNOWN)
    confidence_threshold = models.FloatField(default=0.25)
    iou_threshold = models.FloatField(default=0.45)
    preprocess_mode = models.CharField(max_length=16, default="off")
    preprocess_profile = models.CharField(max_length=32, blank=True, default="")
    preprocess_algorithms = models.JSONField(default=list, blank=True)
    preprocess_algorithm_params = models.JSONField(default=dict, blank=True)
    preprocess_enable_gamma = models.BooleanField(default=False)
    runtime_options = models.JSONField(default=dict, blank=True)
    requested_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="detection_tasks",
    )
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "detection_tasks"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["task_no"]),
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
        ]


class InferenceRecord(models.Model):
    task = models.ForeignKey(DetectionTask, on_delete=models.CASCADE, related_name="inference_records")
    engine_type = models.CharField(max_length=64)
    engine_version = models.CharField(max_length=64, blank=True)
    model_name = models.CharField(max_length=128, blank=True)
    model_version = models.CharField(max_length=64, blank=True)
    request_payload = models.JSONField(default=dict, blank=True)
    response_payload = models.JSONField(default=dict, blank=True)
    result_image_path = models.CharField(max_length=255, blank=True)
    result_image_url = models.CharField(max_length=255, blank=True)
    object_count = models.PositiveIntegerField(default=0)
    avg_confidence = models.FloatField(null=True, blank=True)
    duration_ms = models.PositiveIntegerField(default=0)
    is_mock = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "inference_records"
        ordering = ["-created_at"]


class DetectionObject(models.Model):
    record = models.ForeignKey(InferenceRecord, on_delete=models.CASCADE, related_name="objects")
    class_name = models.CharField(max_length=128)
    class_id = models.IntegerField()
    confidence = models.FloatField()
    bbox_x1 = models.IntegerField()
    bbox_y1 = models.IntegerField()
    bbox_x2 = models.IntegerField()
    bbox_y2 = models.IntegerField()
    bbox_width = models.IntegerField()
    bbox_height = models.IntegerField()
    area_ratio = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "detection_objects"
        ordering = ["-confidence", "-created_at"]
        indexes = [models.Index(fields=["class_name"])]
