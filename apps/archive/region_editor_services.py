"""Persist explicit user-drawn geometry without musical association or approval."""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F

from apps.archive import models as m
from apps.archive.content_geometry_services import append_region
from apps.archive.ocr_services import selection_bounds, validate
from apps.archive.preview_services import preview_bytes, preview_file
from apps.archive.services import ArchiveConflict
from core.page_geometry import PageGeometry


def save_rectangle(
    file_id,
    *,
    expected_file_revision,
    source_version_id,
    selection,
    region_id=None,
    expected_region_number=0,
    using="default",
):
    """Create or revise an unconfirmed region pinned to known original geometry.

    No source-page backfill, edition, assignment, inspection or confirmation is
    implied. A stale file or region rejects the whole transaction. Existing
    logical revisions continue to pin their earlier immutable region revision.
    """
    payload = validate({"file_id": str(file_id), "selection": selection})
    file = preview_file(payload["file_id"], using=using)
    if file.kind != "BASE":
        raise ValidationError("Regions require the exact unchanged source publication.")
    # Verify authorized receipt/snapshot bytes before opening a short DB writer
    # transaction. No PDF parser or filesystem operation runs under its lock.
    preview_bytes(file)
    with transaction.atomic(using=using):
        if not m.ArchiveFile.objects.using(using).filter(pk=file.pk).update(revision=F("revision")):
            raise ArchiveConflict()
        file.refresh_from_db(using=using)
        if (
            type(expected_file_revision) is not int
            or expected_file_revision != file.revision
            or str(source_version_id) != str(file.source_version_id)
        ):
            raise ArchiveConflict()
        page = (
            m.SourcePage.objects.using(using)
            .filter(source_version_id=file.source_version_id, page_index=payload["selection"]["page"])
            .first()
        )
        if page is None or page.original_crop_box is None:
            raise ValidationError("Inspected original source geometry is required for regions.")
        geometry = PageGeometry(page.media_box, page.original_crop_box, page.rotation, page.user_unit)
        bounds = selection_bounds(geometry, payload["selection"]["box"])
        if region_id is None:
            if type(expected_region_number) is not int or expected_region_number != 0:
                raise ArchiveConflict()
            region = m.PageRegion.objects.using(using).create(source_page=page)
        else:
            region = m.PageRegion.objects.using(using).filter(pk=region_id, source_page=page).first()
            if region is None:
                raise ValidationError("Region does not belong to the selected exact source page.")
        return append_region(region.pk, expected_number=expected_region_number, bounds_points=bounds, using=using)
