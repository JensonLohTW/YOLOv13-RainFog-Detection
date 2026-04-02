from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class SystemConfigItem(models.Model):
    class ValueType(models.TextChoices):
        STRING = "string", "String"
        BOOLEAN = "boolean", "Boolean"
        INTEGER = "integer", "Integer"
        FLOAT = "float", "Float"
        URL = "url", "URL"

    config_key = models.CharField(max_length=128, unique=True)
    config_value = models.TextField()
    value_type = models.CharField(max_length=16, choices=ValueType.choices, default=ValueType.STRING)
    is_sensitive = models.BooleanField(default=False)
    description = models.CharField(max_length=255, blank=True)
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_system_configs",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "system_config_items"
        ordering = ["config_key"]
