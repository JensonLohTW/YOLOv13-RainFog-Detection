from __future__ import annotations

from typing import Any

from mcp_services.common.errors import MCPFacadeError
from mcp_services.common.settings import TrainingMCPSettings

from .django_bootstrap import bootstrap_django
from .schemas import CreateTrainingJobInput


class TrainingMCPFacade:
    """封裝訓練資料集與任務能力，供 MCP 介面重用。"""

    def __init__(self, settings: TrainingMCPSettings | None = None) -> None:
        self.settings = settings or TrainingMCPSettings()
        bootstrap_django(self.settings.django_settings_module)

    def list_datasets(self) -> dict[str, Any]:
        training_dataset_model = self._get_training_dataset_model()
        items = training_dataset_model.objects.all()
        serializer = self._get_dataset_serializer()(items, many=True)
        return {"items": serializer.data, "total": items.count()}

    def list_jobs(self, status_filter: str = "") -> dict[str, Any]:
        training_job_model = self._get_training_job_model()
        queryset = training_job_model.objects.select_related("dataset").all()
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        items = self._get_job_service().refresh_jobs(list(queryset))
        serializer = self._get_job_serializer()(items, many=True)
        return {"items": serializer.data, "total": len(items)}

    def create_job(self, payload: CreateTrainingJobInput) -> dict[str, Any]:
        training_dataset_model = self._get_training_dataset_model()
        try:
            dataset = training_dataset_model.objects.get(
                pk=payload.dataset_id,
                status=training_dataset_model.Status.READY,
            )
        except training_dataset_model.DoesNotExist as exc:
            raise MCPFacadeError("資料集不存在或尚未就緒。") from exc

        job_service = self._get_job_service()
        job = job_service.create_job(
            dataset=dataset,
            model_file=payload.model_file,
            epochs=payload.epochs,
            batch=payload.batch,
            imgsz=payload.imgsz,
            device=payload.device,
            workers=payload.workers,
            patience=payload.patience,
            preprocess_mode=payload.preprocess_mode,
            preprocess_profile=payload.preprocess_profile,
            preprocess_algorithms=payload.preprocess_algorithms,
            preprocess_algorithm_params=payload.preprocess_algorithm_params,
            preprocess_enable_gamma=payload.preprocess_enable_gamma,
        )
        started_job = job_service.start_job(job)
        return self._serialize_job(started_job)

    def get_job_detail(self, job_id: int) -> dict[str, Any]:
        job = self._get_job_or_raise(job_id)
        refreshed_job = self._get_job_service().refresh_job(job)
        return self._serialize_job(refreshed_job)

    def cancel_job(self, job_id: int) -> dict[str, Any]:
        job = self._get_job_or_raise(job_id)
        updated_job = self._get_job_service().cancel_job(job)
        return self._serialize_job(updated_job)

    def retry_job(self, job_id: int) -> dict[str, Any]:
        job = self._get_job_or_raise(job_id)
        try:
            retried_job = self._get_job_service().retry_job(job)
        except ValueError as exc:
            raise MCPFacadeError(str(exc)) from exc
        return self._serialize_job(retried_job)

    def deploy_job(self, job_id: int, model_alias: str = "") -> dict[str, Any]:
        job = self._get_job_or_raise(job_id)
        try:
            return self._get_job_service().deploy_job(job, model_alias or None)
        except (ValueError, FileNotFoundError) as exc:
            raise MCPFacadeError(str(exc)) from exc

    def validate_baseline(self, job_id: int) -> dict[str, Any]:
        job = self._get_job_or_raise(job_id)
        try:
            updated_job = self._get_job_service().validate_baseline(job)
        except ValueError as exc:
            raise MCPFacadeError(str(exc)) from exc
        return self._serialize_job(updated_job)

    def get_job_log(self, job_id: int) -> dict[str, Any]:
        job = self._get_job_or_raise(job_id)
        log_text = self._get_job_service()._read_log_tail(
            job.log_path,
            lines=self.settings.log_tail_lines,
        )
        return {"job_id": job_id, "log_path": job.log_path, "log": log_text}

    def get_job_visualization(self, job_id: int) -> dict[str, Any]:
        job = self._get_job_or_raise(job_id)
        return self._get_job_service().get_visualization_payload(job)

    def _get_job_or_raise(self, job_id: int):
        training_job_model = self._get_training_job_model()
        try:
            return training_job_model.objects.select_related("dataset").get(pk=job_id)
        except training_job_model.DoesNotExist as exc:
            raise MCPFacadeError(f"找不到訓練任務：{job_id}") from exc

    def _serialize_job(self, job) -> dict[str, Any]:
        serializer = self._get_job_serializer()(job)
        return dict(serializer.data)

    def _get_training_dataset_model(self):
        from apps.training.models import TrainingDataset

        return TrainingDataset

    def _get_training_job_model(self):
        from apps.training.models import TrainingJob

        return TrainingJob

    def _get_dataset_serializer(self):
        from apps.training.serializers import TrainingDatasetSerializer

        return TrainingDatasetSerializer

    def _get_job_serializer(self):
        from apps.training.serializers import TrainingJobSerializer

        return TrainingJobSerializer

    def _get_job_service(self):
        from apps.training.services.job_service import TrainingJobService

        return TrainingJobService()
