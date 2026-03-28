from django.urls import path

from .views import ImageAssetDetailView, ImageAssetListView, ImageAssetUploadView

urlpatterns = [
    path("upload", ImageAssetUploadView.as_view(), name="image-upload"),
    path("", ImageAssetListView.as_view(), name="image-list"),
    path("<int:image_id>", ImageAssetDetailView.as_view(), name="image-detail"),
]
