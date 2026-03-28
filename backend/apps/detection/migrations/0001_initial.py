from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("media", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="DetectionTask",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("task_no", models.CharField(max_length=32, unique=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "Pending"),
                            ("QUEUED", "Queued"),
                            ("PROCESSING", "Processing"),
                            ("SUCCESS", "Success"),
                            ("FAILED", "Failed"),
                            ("CANCELED", "Canceled"),
                        ],
                        default="PENDING",
                        max_length=16,
                    ),
                ),
                (
                    "trigger_mode",
                    models.CharField(
                        choices=[("manual", "Manual"), ("batch", "Batch"), ("api", "API")],
                        default="manual",
                        max_length=16,
                    ),
                ),
                (
                    "source_type",
                    models.CharField(
                        choices=[("image_upload", "Image Upload"), ("historical_replay", "Historical Replay")],
                        default="image_upload",
                        max_length=32,
                    ),
                ),
                (
                    "weather_scene",
                    models.CharField(
                        choices=[
                            ("rain", "Rain"),
                            ("fog", "Fog"),
                            ("rain_fog", "Rain + Fog"),
                            ("unknown", "Unknown"),
                        ],
                        default="unknown",
                        max_length=16,
                    ),
                ),
                ("confidence_threshold", models.FloatField(default=0.25)),
                ("iou_threshold", models.FloatField(default=0.45)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("error_message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "image",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="detection_tasks",
                        to="media.imageasset",
                    ),
                ),
                (
                    "requested_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="detection_tasks",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "detection_tasks",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="InferenceRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("engine_type", models.CharField(max_length=64)),
                ("engine_version", models.CharField(blank=True, max_length=64)),
                ("model_name", models.CharField(blank=True, max_length=128)),
                ("model_version", models.CharField(blank=True, max_length=64)),
                ("request_payload", models.JSONField(blank=True, default=dict)),
                ("response_payload", models.JSONField(blank=True, default=dict)),
                ("result_image_path", models.CharField(blank=True, max_length=255)),
                ("result_image_url", models.CharField(blank=True, max_length=255)),
                ("object_count", models.PositiveIntegerField(default=0)),
                ("avg_confidence", models.FloatField(blank=True, null=True)),
                ("duration_ms", models.PositiveIntegerField(default=0)),
                ("is_mock", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "task",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="inference_records",
                        to="detection.detectiontask",
                    ),
                ),
            ],
            options={
                "db_table": "inference_records",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="DetectionObject",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("class_name", models.CharField(max_length=128)),
                ("class_id", models.IntegerField()),
                ("confidence", models.FloatField()),
                ("bbox_x1", models.IntegerField()),
                ("bbox_y1", models.IntegerField()),
                ("bbox_x2", models.IntegerField()),
                ("bbox_y2", models.IntegerField()),
                ("bbox_width", models.IntegerField()),
                ("bbox_height", models.IntegerField()),
                ("area_ratio", models.FloatField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "record",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="objects",
                        to="detection.inferencerecord",
                    ),
                ),
            ],
            options={
                "db_table": "detection_objects",
                "ordering": ["-confidence", "-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="detectiontask",
            index=models.Index(fields=["task_no"], name="detection_t_task_no_f8a0dc_idx"),
        ),
        migrations.AddIndex(
            model_name="detectiontask",
            index=models.Index(fields=["status"], name="detection_t_status_18144a_idx"),
        ),
        migrations.AddIndex(
            model_name="detectiontask",
            index=models.Index(fields=["created_at"], name="detection_t_created_e9bfae_idx"),
        ),
        migrations.AddIndex(
            model_name="detectionobject",
            index=models.Index(fields=["class_name"], name="detection_o_class_n_dcd9a1_idx"),
        ),
    ]
