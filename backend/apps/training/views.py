from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.views import APIView

from common.api.response import success_response

from .models import TrainingDataset, TrainingJob
from .serializers import (
    DatasetUploadSerializer,
    JobDeploySerializer,
    TrainingDatasetSerializer,
    TrainingJobCreateSerializer,
    TrainingJobSerializer,
)
from .services.dataset_service import DatasetService
from .services.job_service import TrainingJobService


class DatasetUploadView(APIView):
    authentication_classes = []
    permission_classes = []
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):  # noqa: ANN001
        serializer = DatasetUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        dataset = DatasetService().upload_and_prepare(
            zip_file=d["file"],
            name=d["name"],
            description=d.get("description", ""),
            val_ratio=d.get("val_ratio", 0.2),
        )
        return success_response(
            TrainingDatasetSerializer(dataset).data,
            message="資料集上傳並處理完成",
            status=status.HTTP_201_CREATED,
        )


class DatasetListView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):  # noqa: ANN001
        items = TrainingDataset.objects.all()
        return success_response(
            {
                "items": TrainingDatasetSerializer(items, many=True).data,
                "total": items.count(),
            }
        )


class DatasetDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, dataset_id):  # noqa: ANN001
        try:
            dataset = TrainingDataset.objects.get(pk=dataset_id)
        except TrainingDataset.DoesNotExist:
            return success_response({}, message="資料集不存在", status=status.HTTP_404_NOT_FOUND)
        return success_response(TrainingDatasetSerializer(dataset).data)

    def delete(self, request, dataset_id):  # noqa: ANN001
        try:
            dataset = TrainingDataset.objects.get(pk=dataset_id)
        except TrainingDataset.DoesNotExist:
            return success_response({}, message="資料集不存在", status=status.HTTP_404_NOT_FOUND)
        dataset.delete()
        return success_response({}, message="資料集已刪除")


class TrainingJobListCreateView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):  # noqa: ANN001
        qs = TrainingJob.objects.select_related("dataset").all()
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return success_response(
            {
                "items": TrainingJobSerializer(qs, many=True).data,
                "total": qs.count(),
            }
        )

    def post(self, request):  # noqa: ANN001
        serializer = TrainingJobCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        dataset = TrainingDataset.objects.get(pk=d["dataset_id"])
        svc = TrainingJobService()
        job = svc.create_job(
            dataset=dataset,
            model_file=d["model_file"],
            epochs=d["epochs"],
            batch=d["batch"],
            imgsz=d["imgsz"],
            device=d["device"],
            workers=d["workers"],
            patience=d["patience"],
        )
        job = svc.start_job(job)
        return success_response(
            TrainingJobSerializer(job).data,
            message="訓練任務已啟動",
            status=status.HTTP_201_CREATED,
        )


class TrainingJobDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, job_id):  # noqa: ANN001
        try:
            job = TrainingJob.objects.select_related("dataset").get(pk=job_id)
        except TrainingJob.DoesNotExist:
            return success_response({}, message="任務不存在", status=status.HTTP_404_NOT_FOUND)
        svc = TrainingJobService()
        job = svc.refresh_progress(job)
        job = svc.refresh_baseline(job)
        return success_response(TrainingJobSerializer(job).data)


class TrainingJobCancelView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, job_id):  # noqa: ANN001
        try:
            job = TrainingJob.objects.get(pk=job_id)
        except TrainingJob.DoesNotExist:
            return success_response({}, message="任務不存在", status=status.HTTP_404_NOT_FOUND)
        job = TrainingJobService().cancel_job(job)
        return success_response(TrainingJobSerializer(job).data, message="任務已取消")


class TrainingJobDeployView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, job_id):  # noqa: ANN001
        try:
            job = TrainingJob.objects.get(pk=job_id)
        except TrainingJob.DoesNotExist:
            return success_response({}, message="任務不存在", status=status.HTTP_404_NOT_FOUND)
        serializer = JobDeploySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        alias = serializer.validated_data.get("model_alias") or None
        try:
            result = TrainingJobService().deploy_job(job, alias)
        except (ValueError, FileNotFoundError) as exc:
            return success_response({}, message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(result, message="模型已成功部署至推理服務")


class TrainingJobBaselineView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, job_id):  # noqa: ANN001
        try:
            job = TrainingJob.objects.select_related("dataset").get(pk=job_id)
        except TrainingJob.DoesNotExist:
            return success_response({}, message="任務不存在", status=status.HTTP_404_NOT_FOUND)
        try:
            job = TrainingJobService().validate_baseline(job)
        except ValueError as exc:
            return success_response({}, message=str(exc), status=status.HTTP_400_BAD_REQUEST)
        return success_response(TrainingJobSerializer(job).data, message="基線驗證已啟動")


class TrainingJobLogView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, job_id):  # noqa: ANN001
        try:
            job = TrainingJob.objects.get(pk=job_id)
        except TrainingJob.DoesNotExist:
            return success_response({}, message="任務不存在", status=status.HTTP_404_NOT_FOUND)
        tail = TrainingJobService._read_log_tail(job.log_path, lines=100)
        return success_response({"log": tail, "log_path": job.log_path})
