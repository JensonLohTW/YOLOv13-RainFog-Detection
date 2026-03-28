from rest_framework import serializers

from .models import OperationLog


class OperationLogSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = OperationLog
        fields = [
            "id",
            "module",
            "action",
            "method",
            "path",
            "ip",
            "request_body",
            "response_code",
            "status",
            "duration_ms",
            "user_name",
            "created_at",
        ]

    def get_user_name(self, obj):  # noqa: ANN001
        return obj.user.username if obj.user else ""
