from django.urls import path

from .views import (
    DatasetDetailView,
    DatasetListView,
    DatasetUploadView,
    TrainingJobBaselineView,
    TrainingJobCancelView,
    TrainingJobDeployView,
    TrainingJobDetailView,
    TrainingJobListCreateView,
    TrainingJobLogView,
    TrainingJobRetryView,
    TrainingJobVisualizationView,
)

urlpatterns = [
    path("datasets/upload", DatasetUploadView.as_view(), name="training-dataset-upload"),
    path("datasets", DatasetListView.as_view(), name="training-dataset-list"),
    path("datasets/<int:dataset_id>", DatasetDetailView.as_view(), name="training-dataset-detail"),
    path("jobs", TrainingJobListCreateView.as_view(), name="training-job-list-create"),
    path("jobs/<int:job_id>", TrainingJobDetailView.as_view(), name="training-job-detail"),
    path("jobs/<int:job_id>/cancel", TrainingJobCancelView.as_view(), name="training-job-cancel"),
    path("jobs/<int:job_id>/retry", TrainingJobRetryView.as_view(), name="training-job-retry"),
    path("jobs/<int:job_id>/deploy", TrainingJobDeployView.as_view(), name="training-job-deploy"),
    path("jobs/<int:job_id>/validate-baseline", TrainingJobBaselineView.as_view(), name="training-job-baseline"),
    path("jobs/<int:job_id>/log", TrainingJobLogView.as_view(), name="training-job-log"),
    path("jobs/<int:job_id>/visualization", TrainingJobVisualizationView.as_view(), name="training-job-visualization"),
]
