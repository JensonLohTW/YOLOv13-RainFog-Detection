from rest_framework import serializers

from .models import TrainingDataset, TrainingJob
from pathlib import Path


class TrainingDatasetSerializer(serializers.ModelSerializer):
    class_names = serializers.SerializerMethodField()

    class Meta:
        model = TrainingDataset
        fields = [
            "id", "name", "description", "zip_original_name",
            "dataset_path", "num_train", "num_val", "num_classes",
            "class_names", "status", "error_message", "created_at",
        ]

    def get_class_names(self, obj):  # noqa: ANN001
        return obj.class_names


class DatasetUploadSerializer(serializers.Serializer):
    file = serializers.FileField(required=True)
    name = serializers.CharField(max_length=128)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    val_ratio = serializers.FloatField(required=False, default=0.2, min_value=0.05, max_value=0.5)

    def validate_file(self, value):  # noqa: ANN001
        if not value.name.lower().endswith(".zip"):
            raise serializers.ValidationError("只支援 .zip 格式的資料集壓縮包。")
        return value

    def validate_name(self, value):  # noqa: ANN001
        if TrainingDataset.objects.filter(name=value).exists():
            raise serializers.ValidationError(f"資料集名稱 '{value}' 已存在。")
        return value


class TrainingJobCreateSerializer(serializers.Serializer):
    dataset_id = serializers.IntegerField()
    model_file = serializers.CharField(default="yolov13l.pt", max_length=128)
    epochs = serializers.IntegerField(default=50, min_value=1, max_value=500)
    batch = serializers.IntegerField(default=4, min_value=1)
    imgsz = serializers.IntegerField(default=640)
    device = serializers.CharField(default="0", max_length=32)
    workers = serializers.IntegerField(default=0, min_value=0)
    patience = serializers.IntegerField(default=20, min_value=1)
    preprocess_mode = serializers.ChoiceField(choices=["off", "auto", "manual"], default="off")
    preprocess_profile = serializers.CharField(required=False, allow_blank=True, default="")
    preprocess_algorithms = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
    preprocess_algorithm_params = serializers.DictField(required=False, default=dict)
    preprocess_enable_gamma = serializers.BooleanField(required=False, default=False)

    def validate_dataset_id(self, value):  # noqa: ANN001
        if not TrainingDataset.objects.filter(pk=value, status=TrainingDataset.Status.READY).exists():
            raise serializers.ValidationError("資料集不存在或尚未就緒。")
        return value


class TrainingJobSerializer(serializers.ModelSerializer):
    dataset_id = serializers.SerializerMethodField()
    dataset_name = serializers.SerializerMethodField()
    progress_pct = serializers.SerializerMethodField()
    improvement_map50 = serializers.SerializerMethodField()
    can_cancel = serializers.SerializerMethodField()
    can_retry = serializers.SerializerMethodField()
    can_deploy = serializers.SerializerMethodField()
    has_metrics = serializers.SerializerMethodField()
    has_summary = serializers.SerializerMethodField()

    class Meta:
        model = TrainingJob
        fields = [
            "id", "job_no", "dataset_id", "dataset_name", "model_file",
            "epochs", "batch", "imgsz", "device", "workers", "patience",
            "preprocess_mode", "preprocess_profile", "preprocess_algorithms",
            "preprocess_algorithm_params", "preprocess_enable_gamma",
            "run_name", "run_dir", "log_path", "best_pt_path",
            "prepared_dataset_path", "preprocess_manifest_path",
            "status", "pid", "current_epoch", "total_epochs",
            "best_map50", "best_map50_95", "error_message",
            "baseline_map50", "baseline_map50_95",
            "baseline_precision", "baseline_recall", "baseline_status",
            "progress_pct", "improvement_map50", "can_cancel", "can_retry",
            "can_deploy", "has_metrics", "has_summary",
            "started_at", "finished_at", "created_at",
        ]

    def get_dataset_id(self, obj):  # noqa: ANN001
        return obj.dataset_id

    def get_dataset_name(self, obj):  # noqa: ANN001
        return obj.dataset.name if obj.dataset else ""

    def get_progress_pct(self, obj):  # noqa: ANN001
        if obj.total_epochs == 0:
            return 0
        return round(obj.current_epoch / obj.total_epochs * 100, 1)

    def get_improvement_map50(self, obj):  # noqa: ANN001
        if obj.best_map50 is None or obj.baseline_map50 is None:
            return None
        return round(obj.best_map50 - obj.baseline_map50, 6)

    def get_can_cancel(self, obj):  # noqa: ANN001
        return obj.status in (TrainingJob.Status.PENDING, TrainingJob.Status.RUNNING)

    def get_can_retry(self, obj):  # noqa: ANN001
        return obj.status in (
            TrainingJob.Status.COMPLETED,
            TrainingJob.Status.FAILED,
            TrainingJob.Status.CANCELED,
        )

    def get_can_deploy(self, obj):  # noqa: ANN001
        return obj.status == TrainingJob.Status.COMPLETED and bool(obj.best_pt_path)

    def get_has_metrics(self, obj):  # noqa: ANN001
        run_dir = Path(obj.run_dir)
        return (run_dir / "metrics_raw.json").exists() or (run_dir / "results.csv").exists()

    def get_has_summary(self, obj):  # noqa: ANN001
        return (Path(obj.run_dir) / "training_summary.csv").exists()


class JobDeploySerializer(serializers.Serializer):
    model_alias = serializers.CharField(required=False, allow_blank=True, default="")
