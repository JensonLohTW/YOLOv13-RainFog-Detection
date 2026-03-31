from django.db import transaction

from .models import ImageAsset


class ImageAssetService:
    @transaction.atomic
    def upload(self, uploaded_file, user=None):  # noqa: ANN001, ANN201
        metadata = ImageAsset.build_metadata(uploaded_file)
        existing = ImageAsset.objects.filter(sha256=metadata["sha256"]).first()
        if existing:
            return existing

        image = ImageAsset(
            file=uploaded_file,
            uploaded_by=user if user and getattr(user, "is_authenticated", False) else None,
            **metadata,
        )
        image.save()
        return image
