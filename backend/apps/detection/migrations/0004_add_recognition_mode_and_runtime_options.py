from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("detection", "0003_add_preprocess_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="detectiontask",
            name="recognition_mode",
            field=models.CharField(
                choices=[("scene_default", "Scene Default"), ("image", "Image")],
                default="scene_default",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="detectiontask",
            name="runtime_options",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
