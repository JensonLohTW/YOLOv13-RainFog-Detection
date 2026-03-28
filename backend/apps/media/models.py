import hashlib
import os
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

User = get_user_model()


def upload_to_image_asset(instance, filename):  # noqa: ANN001
    ext = Path(filename).suffix.lower()
    now = instance.created_at or timezone.now()
    return f"images/{now:%Y/%m/%d}/{uuid4().hex}{ext}"


class ImageAsset(models.Model):
    class StorageType(models.TextChoices):
        LOCAL = "local", "Local"

    file = models.ImageField(upload_to=upload_to_image_asset, max_length=255)
    original_name = models.CharField(max_length=255)
    file_name = models.CharField(max_length=255)
    file_ext = models.CharField(max_length=32, blank=True)
    mime_type = models.CharField(max_length=128, blank=True)
    file_size = models.PositiveBigIntegerField(default=0)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    sha256 = models.CharField(max_length=64, unique=True)
    storage_type = models.CharField(
        max_length=32,
        choices=StorageType.choices,
        default=StorageType.LOCAL,
    )
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_images",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "image_assets"
        ordering = ["-created_at"]

    @property
    def file_url(self) -> str:
        if not self.file:
            return ""
        return f"{settings.MEDIA_URL}{self.file.name}"

    @classmethod
    def calculate_sha256(cls, uploaded_file) -> str:  # noqa: ANN206
        hasher = hashlib.sha256()
        for chunk in uploaded_file.chunks():
            hasher.update(chunk)
        uploaded_file.seek(0)
        return hasher.hexdigest()

    @classmethod
    def build_metadata(cls, uploaded_file) -> dict:  # noqa: ANN206
        original_name = uploaded_file.name
        file_ext = Path(original_name).suffix.lower()
        mime_type = getattr(uploaded_file, "content_type", "") or ""
        image = getattr(uploaded_file, "image", None)
        image_width = getattr(image, "width", None)
        image_height = getattr(image, "height", None)
        return {
            "original_name": original_name,
            "file_name": os.path.basename(original_name),
            "file_ext": file_ext,
            "mime_type": mime_type,
            "file_size": uploaded_file.size,
            "width": image_width,
            "height": image_height,
            "sha256": cls.calculate_sha256(uploaded_file),
        }
