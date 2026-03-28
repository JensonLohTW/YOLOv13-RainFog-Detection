from rest_framework import serializers

from .models import ImageAsset


class ImageAssetUploadSerializer(serializers.Serializer):
    image = serializers.ImageField(required=True)

    def validate_image(self, value):  # noqa: ANN001
        allowed_types = {"image/jpeg", "image/png", "image/webp"}
        if value.content_type not in allowed_types:
            raise serializers.ValidationError("Only jpg, png and webp images are supported.")
        return value


class ImageAssetSerializer(serializers.ModelSerializer):
    file_url = serializers.ReadOnlyField()
    uploaded_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ImageAsset
        fields = [
            "id",
            "original_name",
            "file_name",
            "file_ext",
            "mime_type",
            "file_size",
            "width",
            "height",
            "sha256",
            "storage_type",
            "file_url",
            "uploaded_by",
            "uploaded_by_name",
            "created_at",
        ]

    def get_uploaded_by_name(self, obj):  # noqa: ANN001
        if not obj.uploaded_by:
            return ""
        return getattr(obj.uploaded_by, "username", "")
