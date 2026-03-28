from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="OperationLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("module", models.CharField(blank=True, max_length=64)),
                ("action", models.CharField(blank=True, max_length=64)),
                ("method", models.CharField(max_length=16)),
                ("path", models.CharField(max_length=255)),
                ("ip", models.CharField(blank=True, max_length=64)),
                ("request_body", models.TextField(blank=True)),
                ("response_code", models.PositiveIntegerField(default=200)),
                (
                    "status",
                    models.CharField(
                        choices=[("success", "Success"), ("error", "Error")],
                        default="success",
                        max_length=16,
                    ),
                ),
                ("duration_ms", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="operation_logs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "operation_logs",
                "ordering": ["-created_at"],
            },
        ),
    ]
