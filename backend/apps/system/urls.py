from django.urls import path

from .views import SystemConfigDetailView, SystemConfigListView

urlpatterns = [
    path("configs", SystemConfigListView.as_view(), name="system-configs"),
    path("configs/<int:config_id>", SystemConfigDetailView.as_view(), name="system-config-detail"),
]
