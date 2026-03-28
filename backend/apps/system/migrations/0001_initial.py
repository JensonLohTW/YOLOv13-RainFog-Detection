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
            name="SystemConfigItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("config_key", models.CharField(max_length=128, unique=True)),
                ("config_value", models.TextField()),
                (
                    "value_type",
                    models.CharField(
                        choices=[
                            ("string", "String"),
                            ("boolean", "Boolean"),
                            ("integer", "Integer"),
                            ("float", "Float"),
                            ("url", "URL"),
                        ],
                        default="string",
                        max_length=16,
                    ),
                ),
                ("description", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="updated_system_configs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "system_config_items",
                "ordering": ["config_key"],
            },
        ),
    ]
