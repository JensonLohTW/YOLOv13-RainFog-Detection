from django.urls import path

from .views import (
    DetectionExplanationView,
    DetectionTaskDetailView,
    DetectionTaskListCreateView,
    DetectionTaskRetryView,
    PreprocessPreviewView,
)

urlpatterns = [
    path("tasks", DetectionTaskListCreateView.as_view(), name="task-list-create"),
    path("tasks/<str:task_no>", DetectionTaskDetailView.as_view(), name="task-detail"),
    path("tasks/<str:task_no>/retry", DetectionTaskRetryView.as_view(), name="task-retry"),
    path("preprocess-preview", PreprocessPreviewView.as_view(), name="preprocess-preview"),
    path("explanations", DetectionExplanationView.as_view(), name="task-explanation"),
]
