from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.views import APIView

from apps.media.models import ImageAsset
from common.api.response import success_response

from .models import DetectionTask, InferenceRecord
from .serializers import DetectionTaskCreateSerializer, DetectionTaskDetailSerializer, DetectionTaskListSerializer
from .services import DetectionRequest, DetectionTaskService


def build_detection_queryset():
    # 任務列表與詳情頁共用同一套查詢預載，減少重複 SQL。
    return DetectionTask.objects.select_related("image").prefetch_related(
        Prefetch("inference_records", queryset=InferenceRecord.objects.prefetch_related("objects"))
    )


class DetectionTaskListCreateView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):  # noqa: ANN001
        queryset = build_detection_queryset()
        status_value = request.query_params.get("status")
        weather_scene = request.query_params.get("weather_scene")
        keyword = request.query_params.get("keyword")

        if status_value:
            queryset = queryset.filter(status=status_value)
        if weather_scene:
            queryset = queryset.filter(weather_scene=weather_scene)
        if keyword:
            queryset = queryset.filter(Q(task_no__icontains=keyword) | Q(image__original_name__icontains=keyword))

        tasks = queryset[:50]
        serializer = DetectionTaskListSerializer(tasks, many=True)
        return success_response({"items": serializer.data, "total": queryset.count()})

    def post(self, request):  # noqa: ANN001
        serializer = DetectionTaskCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        image = ImageAsset.objects.get(pk=payload["image_id"])
        task = DetectionTaskService().create_and_run(
            DetectionRequest(
                image=image,
                weather_scene=payload["weather_scene"],
                confidence_threshold=payload["confidence_threshold"],
                iou_threshold=payload["iou_threshold"],
                preprocess_mode=payload["preprocess_mode"],
                preprocess_profile=payload["preprocess_profile"],
                preprocess_algorithms=payload["preprocess_algorithms"],
                preprocess_algorithm_params=payload["preprocess_algorithm_params"],
                preprocess_enable_gamma=payload["preprocess_enable_gamma"],
                requested_by=getattr(request, "user", None),
            )
        )
        return success_response(DetectionTaskDetailSerializer(task).data, status=status.HTTP_201_CREATED)


class DetectionTaskDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, task_no):  # noqa: ANN001
        task = get_object_or_404(build_detection_queryset(), task_no=task_no)
        return success_response(DetectionTaskDetailSerializer(task).data)


class DetectionTaskRetryView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, task_no):  # noqa: ANN001
        task = get_object_or_404(build_detection_queryset(), task_no=task_no)
        retried = DetectionTaskService().retry(task)
        return success_response(DetectionTaskDetailSerializer(retried).data, status=status.HTTP_200_OK)
