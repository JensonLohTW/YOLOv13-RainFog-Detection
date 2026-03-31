from django.conf import settings
from django.contrib import admin
from django.conf.urls.static import static
from django.urls import include, path
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthCheckView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):  # noqa: ANN001
        return Response({"status": "ok", "service": "django-backend"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/health/", HealthCheckView.as_view(), name="health"),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/audit/", include("apps.audit.urls")),
    path("api/v1/images/", include("apps.media.urls")),
    path("api/v1/detection/", include("apps.detection.urls")),
    path("api/v1/dashboard/", include("apps.dashboard.urls")),
    path("api/v1/system/", include("apps.system.urls")),
    path("api/v1/training/", include("apps.training.urls")),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.RESULTS_URL, document_root=settings.RESULTS_ROOT)
