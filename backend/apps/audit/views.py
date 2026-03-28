from rest_framework.views import APIView

from common.api.response import success_response

from .models import OperationLog
from .serializers import OperationLogSerializer


class OperationLogListView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):  # noqa: ANN001
        queryset = OperationLog.objects.all()[:100]
        return success_response(
            {
                "items": OperationLogSerializer(queryset, many=True).data,
                "total": OperationLog.objects.count(),
            }
        )
