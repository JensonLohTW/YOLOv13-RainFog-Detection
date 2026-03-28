from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

import apps.media.models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ImageAsset",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("file", models.ImageField(max_length=255, upload_to=apps.media.models.upload_to_image_asset)),
                ("original_name", models.CharField(max_length=255)),
                ("file_name", models.CharField(max_length=255)),
                ("file_ext", models.CharField(blank=True, max_length=32)),
                ("mime_type", models.CharField(blank=True, max_length=128)),
                ("file_size", models.PositiveBigIntegerField(default=0)),
                ("width", models.PositiveIntegerField(blank=True, null=True)),
                ("height", models.PositiveIntegerField(blank=True, null=True)),
                ("sha256", models.CharField(max_length=64, unique=True)),
                (
                    "storage_type",
                    models.CharField(
                        choices=[("local", "Local")],
                        default="local",
                        max_length=32,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "uploaded_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="uploaded_images",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "image_assets",
                "ordering": ["-created_at"],
            },
        ),
    ]
