from rest_framework import serializers

from apps.media.models import ImageAsset
from apps.media.serializers import ImageAssetSerializer

from .models import DetectionObject, DetectionTask, InferenceRecord


class DetectionTaskCreateSerializer(serializers.Serializer):
    image_id = serializers.IntegerField()
    recognition_mode = serializers.ChoiceField(
        choices=DetectionTask.RecognitionMode.choices,
        required=False,
    )
    weather_scene = serializers.ChoiceField(
        choices=DetectionTask.WeatherScene.choices,
        required=False,
    )
    confidence_threshold = serializers.FloatField(required=False, min_value=0.0, max_value=1.0)
    iou_threshold = serializers.FloatField(required=False, min_value=0.0, max_value=1.0)
    preprocess_mode = serializers.ChoiceField(choices=["off", "auto", "manual"], required=False)
    preprocess_profile = serializers.CharField(required=False, allow_blank=True)
    preprocess_algorithms = serializers.ListField(child=serializers.CharField(), required=False)
    preprocess_algorithm_params = serializers.DictField(required=False)
    preprocess_enable_gamma = serializers.BooleanField(required=False)

    def validate_image_id(self, value):  # noqa: ANN001
        if not ImageAsset.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Image asset does not exist.")
        return value


class PreprocessPreviewSerializer(serializers.Serializer):
    image_id = serializers.IntegerField()
    preprocess_mode = serializers.ChoiceField(choices=["off", "auto", "manual"], default="off")
    preprocess_profile = serializers.CharField(required=False, allow_blank=True, default="")
    preprocess_algorithms = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    preprocess_algorithm_params = serializers.DictField(required=False, default=dict)
    preprocess_enable_gamma = serializers.BooleanField(required=False, default=False)
    scene_hint = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_image_id(self, value):  # noqa: ANN001
        if not ImageAsset.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Image asset does not exist.")
        return value


class DetectionExplanationRequestSerializer(serializers.Serializer):
    task_no = serializers.CharField(required=False, allow_blank=True)
    image_id = serializers.IntegerField(required=False)
    question = serializers.CharField(max_length=500)

    def validate(self, attrs):  # noqa: ANN001
        task_no = attrs.get("task_no", "").strip()
        image_id = attrs.get("image_id")
        if not task_no and image_id is None:
            raise serializers.ValidationError("Either task_no or image_id is required.")
        return attrs

    def validate_image_id(self, value):  # noqa: ANN001
        if not ImageAsset.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Image asset does not exist.")
        return value


class DetectionObjectSerializer(serializers.ModelSerializer):
    bbox = serializers.SerializerMethodField()

    class Meta:
        model = DetectionObject
        fields = [
            "class_id",
            "class_name",
            "confidence",
            "bbox",
            "bbox_width",
            "bbox_height",
            "area_ratio",
        ]

    def get_bbox(self, obj):  # noqa: ANN001
        return [obj.bbox_x1, obj.bbox_y1, obj.bbox_x2, obj.bbox_y2]


class InferenceRecordSerializer(serializers.ModelSerializer):
    objects = DetectionObjectSerializer(many=True, read_only=True)

    class Meta:
        model = InferenceRecord
        fields = [
            "engine_type",
            "engine_version",
            "model_name",
            "model_version",
            "request_payload",
            "response_payload",
            "result_image_path",
            "result_image_url",
            "object_count",
            "avg_confidence",
            "duration_ms",
            "is_mock",
            "created_at",
            "objects",
        ]


class DetectionTaskListSerializer(serializers.ModelSerializer):
    image = ImageAssetSerializer(read_only=True)
    latest_record = serializers.SerializerMethodField()
    object_count = serializers.SerializerMethodField()
    can_retry = serializers.SerializerMethodField()

    class Meta:
        model = DetectionTask
        fields = [
            "task_no",
            "status",
            "recognition_mode",
            "weather_scene",
            "confidence_threshold",
            "iou_threshold",
            "preprocess_mode",
            "preprocess_profile",
            "preprocess_algorithms",
            "preprocess_enable_gamma",
            "image",
            "object_count",
            "latest_record",
            "can_retry",
            "created_at",
            "updated_at",
        ]

    def get_latest_record(self, obj):  # noqa: ANN001
        record = obj.inference_records.first()
        if not record:
            return None
        return {
            "engine_type": record.engine_type,
            "duration_ms": record.duration_ms,
            "is_mock": record.is_mock,
        }

    def get_object_count(self, obj):  # noqa: ANN001
        record = obj.inference_records.first()
        return record.object_count if record else 0

    def get_can_retry(self, obj):  # noqa: ANN001
        return obj.status in {DetectionTask.Status.SUCCESS, DetectionTask.Status.FAILED, DetectionTask.Status.CANCELED}


class DetectionTaskDetailSerializer(serializers.ModelSerializer):
    image = ImageAssetSerializer(read_only=True)
    inference_records = InferenceRecordSerializer(many=True, read_only=True)
    latest_record = serializers.SerializerMethodField()
    can_retry = serializers.SerializerMethodField()

    class Meta:
        model = DetectionTask
        fields = [
            "task_no",
            "status",
            "trigger_mode",
            "source_type",
            "recognition_mode",
            "weather_scene",
            "confidence_threshold",
            "iou_threshold",
            "preprocess_mode",
            "preprocess_profile",
            "preprocess_algorithms",
            "preprocess_algorithm_params",
            "preprocess_enable_gamma",
            "runtime_options",
            "image",
            "started_at",
            "finished_at",
            "error_message",
            "created_at",
            "updated_at",
            "latest_record",
            "can_retry",
            "inference_records",
        ]

    def get_latest_record(self, obj):  # noqa: ANN001
        record = obj.inference_records.first()
        if not record:
            return None
        return InferenceRecordSerializer(record).data

    def get_can_retry(self, obj):  # noqa: ANN001
        return obj.status in {DetectionTask.Status.SUCCESS, DetectionTask.Status.FAILED, DetectionTask.Status.CANCELED}
