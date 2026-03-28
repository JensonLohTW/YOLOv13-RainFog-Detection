from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class OperationLog(models.Model):
    class Status(models.TextChoices):
        SUCCESS = "success", "Success"
        ERROR = "error", "Error"

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="operation_logs",
    )
    module = models.CharField(max_length=64, blank=True)
    action = models.CharField(max_length=64, blank=True)
    method = models.CharField(max_length=16)
    path = models.CharField(max_length=255)
    ip = models.CharField(max_length=64, blank=True)
    request_body = models.TextField(blank=True)
    response_code = models.PositiveIntegerField(default=200)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.SUCCESS)
    duration_ms = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "operation_logs"
        ordering = ["-created_at"]
