from rest_framework import serializers

from .models import SystemConfigItem


class SystemConfigItemSerializer(serializers.ModelSerializer):
    parsed_value = serializers.SerializerMethodField()
    updated_by_name = serializers.SerializerMethodField()

    class Meta:
        model = SystemConfigItem
        fields = [
            "id",
            "config_key",
            "config_value",
            "parsed_value",
            "value_type",
            "description",
            "updated_by",
            "updated_by_name",
            "updated_at",
        ]

    def get_parsed_value(self, obj):  # noqa: ANN001
        if obj.value_type == SystemConfigItem.ValueType.BOOLEAN:
            return obj.config_value.lower() == "true"
        if obj.value_type == SystemConfigItem.ValueType.INTEGER:
            return int(obj.config_value)
        if obj.value_type == SystemConfigItem.ValueType.FLOAT:
            return float(obj.config_value)
        return obj.config_value

    def get_updated_by_name(self, obj):  # noqa: ANN001
        if not obj.updated_by:
            return ""
        return obj.updated_by.username


class SystemConfigItemUpdateSerializer(serializers.Serializer):
    config_value = serializers.CharField()
