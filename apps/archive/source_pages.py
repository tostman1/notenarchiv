"""Materialize the ordered source pages already recorded by PDF validation."""

from uuid import UUID, uuid5

from django.core.exceptions import ValidationError

from core.page_geometry import GeometryError, source_page_geometry_fingerprint

PAGE_NAMESPACE = UUID("7d590e59-ff59-434b-8e52-9ee66a10eedd")


def record_source_pages(page_model, version, *, using, original_crop_boxes=None):
    """Store page geometry, leaving the original CropBox unknown for legacy rows."""
    if original_crop_boxes is not None and len(original_crop_boxes) != len(version.page_info):
        raise ValidationError("Original source geometry does not match the validated page count.")
    pages = page_model.objects.using(using)
    existing = {page.page_index: page for page in pages.filter(source_version_id=version.pk)}
    missing = []
    for index, metadata in enumerate(version.page_info):
        geometry = {
            "media_box": list(metadata["media_box"]),
            "effective_crop_box": list(metadata["crop_box"]),
            "original_crop_box": list(original_crop_boxes[index]) if original_crop_boxes is not None else None,
            "rotation": metadata["rotation"],
            "user_unit": metadata["user_unit"],
        }
        page = existing.pop(index, None)
        if page is not None and original_crop_boxes is None:
            geometry["original_crop_box"] = page.original_crop_box
        try:
            fingerprint = source_page_geometry_fingerprint(**geometry)
        except GeometryError:
            raise ValidationError("Invalid source page geometry.") from None
        if page is None:
            missing.append(
                page_model(
                    id=uuid5(PAGE_NAMESPACE, f"{version.pk}:{index}"),
                    source_version_id=version.pk,
                    page_index=index,
                    geometry_fingerprint=fingerprint,
                    **geometry,
                )
            )
        elif (
            any(getattr(page, name) != value for name, value in geometry.items())
            or page.geometry_fingerprint != fingerprint
        ):
            raise ValidationError("Recorded source page does not match validated PDF metadata.")
    if existing:
        raise ValidationError("Recorded source page index is outside the validated PDF.")
    pages.bulk_create(missing, batch_size=100)
