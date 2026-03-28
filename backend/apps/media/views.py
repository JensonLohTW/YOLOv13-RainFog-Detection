from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.views import APIView

from common.api.response import success_response

from .models import ImageAsset
from .serializers import ImageAssetSerializer, ImageAssetUploadSerializer
from .services import ImageAssetService


class ImageAssetUploadView(APIView):
    authentication_classes = []
    permission_classes = []
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):  # noqa: ANN001
        serializer = ImageAssetUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        image = ImageAssetService().upload(serializer.validated_data["image"], getattr(request, "user", None))
        return success_response(ImageAssetSerializer(image).data, message="image uploaded")


class ImageAssetListView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):  # noqa: ANN001
        items = ImageAsset.objects.all()[:50]
        return success_response(
            {
                "items": ImageAssetSerializer(items, many=True).data,
                "total": ImageAsset.objects.count(),
            }
        )


class ImageAssetDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, image_id):  # noqa: ANN001
        image = ImageAsset.objects.get(pk=image_id)
        return success_response(ImageAssetSerializer(image).data)
