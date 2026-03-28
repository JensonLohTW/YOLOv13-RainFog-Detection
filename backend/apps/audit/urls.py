from django.urls import path

from .views import OperationLogListView

urlpatterns = [
    path("logs", OperationLogListView.as_view(), name="audit-logs"),
]
