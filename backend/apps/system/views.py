from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.views import APIView

from common.api.response import success_response

from .models import SystemConfigItem
from .serializers import SystemConfigItemSerializer, SystemConfigItemUpdateSerializer
from .services import SystemConfigService


class SystemConfigListView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):  # noqa: ANN001
        service = SystemConfigService()
        items = service.list_items()
        return success_response(
            {
                # 同時返回摘要與明細，前端可直接渲染儀表卡片和配置表單。
                "summary": service.summary(),
                "items": SystemConfigItemSerializer(items, many=True).data,
            }
        )


class SystemConfigDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def put(self, request, config_id):  # noqa: ANN001
        item = get_object_or_404(SystemConfigItem, pk=config_id)
        serializer = SystemConfigItemUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated = SystemConfigService().update_item(
            item,
            serializer.validated_data["config_value"],
            getattr(request, "user", None),
        )
        return success_response(SystemConfigItemSerializer(updated).data, status=status.HTTP_200_OK)
