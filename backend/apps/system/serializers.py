from rest_framework import serializers

from .models import SystemConfigItem


class SystemConfigItemSerializer(serializers.ModelSerializer):
    config_value = serializers.SerializerMethodField()
    parsed_value = serializers.SerializerMethodField()
    updated_by_name = serializers.SerializerMethodField()
    display_value = serializers.SerializerMethodField()
    effective_source = serializers.SerializerMethodField()
    has_effective_value = serializers.SerializerMethodField()

    class Meta:
        model = SystemConfigItem
        fields = [
            "id",
            "config_key",
            "config_value",
            "parsed_value",
            "value_type",
            "is_sensitive",
            "display_value",
            "effective_source",
            "has_effective_value",
            "description",
            "updated_by",
            "updated_by_name",
            "updated_at",
        ]

    def get_config_value(self, obj):  # noqa: ANN001
        if obj.is_sensitive:
            return ""
        return obj.config_value

    def get_parsed_value(self, obj):  # noqa: ANN001
        if obj.is_sensitive:
            return None
        if obj.value_type == SystemConfigItem.ValueType.BOOLEAN:
            return obj.config_value.lower() == "true"
        if obj.value_type == SystemConfigItem.ValueType.INTEGER:
            return int(obj.config_value)
        if obj.value_type == SystemConfigItem.ValueType.FLOAT:
            return float(obj.config_value)
        return obj.config_value

    def get_display_value(self, obj):  # noqa: ANN001
        meta = self._runtime_meta(obj)
        return meta["display_value"]

    def get_effective_source(self, obj):  # noqa: ANN001
        meta = self._runtime_meta(obj)
        return meta["effective_source"]

    def get_has_effective_value(self, obj):  # noqa: ANN001
        meta = self._runtime_meta(obj)
        return meta["has_effective_value"]

    def get_updated_by_name(self, obj):  # noqa: ANN001
        if not obj.updated_by:
            return ""
        return obj.updated_by.username

    def _runtime_meta(self, obj):  # noqa: ANN001
        service = self.context.get("system_config_service")
        if service is None:
            return {
                "display_value": obj.config_value,
                "effective_source": "system_config",
                "has_effective_value": bool(obj.config_value),
            }
        return service.build_runtime_meta(obj)


class SystemConfigItemUpdateSerializer(serializers.Serializer):
    config_value = serializers.CharField(allow_blank=True)
