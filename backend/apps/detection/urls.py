from django.urls import path

from .views import DetectionTaskDetailView, DetectionTaskListCreateView, DetectionTaskRetryView

urlpatterns = [
    path("tasks", DetectionTaskListCreateView.as_view(), name="task-list-create"),
    path("tasks/<str:task_no>", DetectionTaskDetailView.as_view(), name="task-detail"),
    path("tasks/<str:task_no>/retry", DetectionTaskRetryView.as_view(), name="task-retry"),
]
