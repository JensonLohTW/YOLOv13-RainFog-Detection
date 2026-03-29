from django.db import migrations, models
import django.db.models.deletion
import apps.training.models


class Migration(migrations.Migration):
    initial = True
    dependencies = []

    operations = [
        migrations.CreateModel(
            name="TrainingDataset",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=128, unique=True)),
                ("description", models.TextField(blank=True)),
                ("zip_original_name", models.CharField(blank=True, max_length=255)),
                ("dataset_path", models.CharField(blank=True, max_length=512)),
                ("num_train", models.PositiveIntegerField(default=0)),
                ("num_val", models.PositiveIntegerField(default=0)),
                ("num_classes", models.PositiveIntegerField(default=0)),
                ("class_names", models.TextField(blank=True, db_column="class_names", default="[]")),
                ("status", models.CharField(choices=[("UPLOADING", "Uploading"), ("READY", "Ready"), ("FAILED", "Failed")], default="UPLOADING", max_length=16)),
                ("error_message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "training_datasets", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="TrainingJob",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("job_no", models.CharField(default=apps.training.models._generate_job_no, max_length=32, unique=True)),
                ("model_file", models.CharField(default="yolov13l.pt", max_length=128)),
                ("epochs", models.PositiveIntegerField(default=50)),
                ("batch", models.IntegerField(default=4)),
                ("imgsz", models.PositiveIntegerField(default=640)),
                ("device", models.CharField(default="0", max_length=32)),
                ("workers", models.PositiveIntegerField(default=0)),
                ("patience", models.PositiveIntegerField(default=20)),
                ("run_name", models.CharField(blank=True, max_length=128)),
                ("run_dir", models.CharField(blank=True, max_length=512)),
                ("log_path", models.CharField(blank=True, max_length=512)),
                ("best_pt_path", models.CharField(blank=True, max_length=512)),
                ("status", models.CharField(choices=[("PENDING", "Pending"), ("RUNNING", "Running"), ("COMPLETED", "Completed"), ("FAILED", "Failed"), ("CANCELED", "Canceled")], default="PENDING", max_length=16)),
                ("pid", models.IntegerField(blank=True, null=True)),
                ("current_epoch", models.IntegerField(default=0)),
                ("total_epochs", models.IntegerField(default=0)),
                ("best_map50", models.FloatField(blank=True, null=True)),
                ("best_map50_95", models.FloatField(blank=True, null=True)),
                ("error_message", models.TextField(blank=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("dataset", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="jobs", to="training.trainingdataset")),
            ],
            options={"db_table": "training_jobs", "ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="trainingjob",
            index=models.Index(fields=["status"], name="training_jo_status_idx"),
        ),
        migrations.AddIndex(
            model_name="trainingjob",
            index=models.Index(fields=["job_no"], name="training_jo_job_no_idx"),
        ),
    ]
