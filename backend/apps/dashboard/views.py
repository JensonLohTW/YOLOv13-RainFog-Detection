from rest_framework.views import APIView

from common.api.response import success_response

from .services import DashboardService


class DashboardOverviewView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):  # noqa: ANN001
        return success_response(DashboardService().overview())
