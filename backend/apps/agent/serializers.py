from rest_framework import serializers

from apps.media.models import ImageAsset


class AgentAskSerializer(serializers.Serializer):
    agent_type = serializers.ChoiceField(choices=["detection_explanation", "analytics_qa"])
    question = serializers.CharField(max_length=500)
    task_no = serializers.CharField(required=False, allow_blank=True)
    image_id = serializers.IntegerField(required=False)

    def validate(self, attrs):  # noqa: ANN001
        agent_type = attrs["agent_type"]
        task_no = attrs.get("task_no", "").strip()
        image_id = attrs.get("image_id")
        if agent_type == "detection_explanation" and not task_no and image_id is None:
            raise serializers.ValidationError("detection_explanation 需要提供 task_no 或 image_id。")
        return attrs

    def validate_image_id(self, value):  # noqa: ANN001
        if not ImageAsset.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Image asset does not exist.")
        return value
