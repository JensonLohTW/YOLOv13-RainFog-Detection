from __future__ import annotations

import json
from uuid import uuid4

from django.db import models
from django.utils import timezone


def _generate_job_no() -> str:
    return f"TJ{timezone.now():%Y%m%d%H%M%S}{uuid4().hex[:6].upper()}"


class TrainingDataset(models.Model):
    class Status(models.TextChoices):
        UPLOADING = "UPLOADING", "Uploading"
        READY = "READY", "Ready"
        FAILED = "FAILED", "Failed"

    name = models.CharField(max_length=128, unique=True)
    description = models.TextField(blank=True)
    zip_original_name = models.CharField(max_length=255, blank=True)
    dataset_path = models.CharField(max_length=512, blank=True)
    num_train = models.PositiveIntegerField(default=0)
    num_val = models.PositiveIntegerField(default=0)
    num_classes = models.PositiveIntegerField(default=0)
    _class_names = models.TextField(db_column="class_names", blank=True, default="[]")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.UPLOADING)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "training_datasets"
        ordering = ["-created_at"]

    @property
    def class_names(self) -> list[str]:
        try:
            return json.loads(self._class_names)
        except (ValueError, TypeError):
            return []

    @class_names.setter
    def class_names(self, value: list[str]) -> None:
        self._class_names = json.dumps(value, ensure_ascii=False)


class TrainingJob(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        RUNNING = "RUNNING", "Running"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"
        CANCELED = "CANCELED", "Canceled"

    job_no = models.CharField(max_length=32, unique=True, default=_generate_job_no)
    dataset = models.ForeignKey(
        TrainingDataset,
        on_delete=models.PROTECT,
        related_name="jobs",
        null=True,
        blank=True,
    )
    model_file = models.CharField(max_length=128, default="yolov13l.pt")
    epochs = models.PositiveIntegerField(default=50)
    batch = models.IntegerField(default=4)
    imgsz = models.PositiveIntegerField(default=640)
    device = models.CharField(max_length=32, default="0")
    workers = models.PositiveIntegerField(default=0)
    patience = models.PositiveIntegerField(default=20)

    run_name = models.CharField(max_length=128, blank=True)
    run_dir = models.CharField(max_length=512, blank=True)
    log_path = models.CharField(max_length=512, blank=True)
    best_pt_path = models.CharField(max_length=512, blank=True)

    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    pid = models.IntegerField(null=True, blank=True)
    current_epoch = models.IntegerField(default=0)
    total_epochs = models.IntegerField(default=0)
    best_map50 = models.FloatField(null=True, blank=True)
    best_map50_95 = models.FloatField(null=True, blank=True)

    baseline_map50 = models.FloatField(null=True, blank=True)
    baseline_map50_95 = models.FloatField(null=True, blank=True)
    baseline_precision = models.FloatField(null=True, blank=True)
    baseline_recall = models.FloatField(null=True, blank=True)
    baseline_status = models.CharField(
        max_length=16,
        default="NONE",
        choices=[("NONE", "None"), ("RUNNING", "Running"), ("DONE", "Done"), ("FAILED", "Failed")],
    )

    error_message = models.TextField(blank=True)

    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "training_jobs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["job_no"]),
        ]
