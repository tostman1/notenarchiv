"""Persist explicit user-drawn geometry without musical association or approval."""

from uuid import UUID

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
    return _save_verified(
        file, payload, expected_file_revision, source_version_id, region_id, expected_region_number, using
    )


def _save_verified(file, payload, expected_file_revision, source_version_id, region_id, expected_region_number, using):
    with transaction.atomic(using=using):
        if not m.ArchiveFile.objects.using(using).filter(pk=file.pk).update(revision=F("revision")):
            raise ArchiveConflict()
        file.refresh_from_db(using=using)
        if file.publication_state != "AVAILABLE":
            raise ValidationError("Source publication became unavailable before geometry was saved.")
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


def split_rectangle(
    file_id,
    *,
    expected_file_revision,
    source_version_id,
    selection,
    axis,
    fraction,
    using="default",
):
    """Create two explicit adjacent regions; retain every existing interpretation.

    Axis and fraction use the displayed normalized rectangle, not PDF coordinates.
    No previous region is deleted/replaced and no musical sequence is inferred.
    Both new identities commit together, after one verified snapshot read outside
    the short SQLite writer transaction.
    """
    payload = validate({"file_id": str(file_id), "selection": selection})
    if axis not in ("horizontal", "vertical") or type(fraction) not in (int, float) or not 0 < fraction < 1:
        raise ValidationError("An interior split position and explicit axis are required.")
    first = list(payload["selection"]["box"])
    second = list(first)
    start, end = (1, 3) if axis == "horizontal" else (0, 2)
    cut = first[start] + (first[end] - first[start]) * fraction
    if not first[start] < cut < first[end]:
        raise ValidationError("Split position cannot produce an empty region.")
    first[end] = cut
    second[start] = cut
    file = preview_file(payload["file_id"], using=using)
    if file.kind != "BASE":
        raise ValidationError("Regions require the exact unchanged source publication.")
    preview_bytes(file)
    with transaction.atomic(using=using):
        revisions = []
        for box in (first, second):
            child = validate({"file_id": str(file.pk), "selection": {"page": selection["page"], "box": box}})
            revisions.append(_save_verified(file, child, expected_file_revision, source_version_id, None, 0, using))
        return tuple(revisions)


def merge_adjacent_regions(
    file_id,
    *,
    expected_file_revision,
    source_version_id,
    region_revision_ids,
    using="default",
):
    """Create one new rectangle from two current adjacent exact-page revisions.

    Gaps, overlap, cross-page inputs and nonrectangular unions are rejected rather
    than silently including additional music. Existing identities and pins remain.
    """
    if not isinstance(region_revision_ids, (list, tuple)) or len(region_revision_ids) != 2:
        raise ValidationError("Select exactly two distinct current region revisions.")
    try:
        identifiers = [value if isinstance(value, UUID) else UUID(value) for value in region_revision_ids]
    except (TypeError, ValueError, AttributeError):
        raise ValidationError("Region revision identifiers must be UUIDs.") from None
    file = preview_file(file_id, using=using)
    if file.kind != "BASE":
        raise ValidationError("Regions require the exact unchanged source publication.")
    preview_bytes(file)
    with transaction.atomic(using=using):
        if not m.ArchiveFile.objects.using(using).filter(pk=file.pk).update(revision=F("revision")):
            raise ArchiveConflict()
        file.refresh_from_db(using=using)
        if file.publication_state != "AVAILABLE":
            raise ValidationError("Source publication became unavailable before geometry was saved.")
        if (
            type(expected_file_revision) is not int
            or expected_file_revision != file.revision
            or str(source_version_id) != str(file.source_version_id)
        ):
            raise ArchiveConflict()
        revisions = list(
            m.PageRegionRevision.objects.using(using)
            .filter(pk__in=identifiers, region__source_page__source_version_id=file.source_version_id)
            .select_related("region__source_page")
        )
        if len(revisions) != 2 or revisions[0].region.source_page_id != revisions[1].region.source_page_id:
            raise ValidationError("Merge requires two distinct regions on the same exact source page.")
        for revision in revisions:
            latest = (
                m.PageRegionRevision.objects.using(using)
                .filter(region_id=revision.region_id)
                .order_by("-number")
                .values_list("pk", flat=True)
                .first()
            )
            if latest != revision.pk:
                raise ArchiveConflict()
        first, second = (revision.bounds_points for revision in revisions)
        vertical = first[1] == second[1] and first[3] == second[3] and (first[2] == second[0] or second[2] == first[0])
        horizontal = (
            first[0] == second[0] and first[2] == second[2] and (first[3] == second[1] or second[3] == first[1])
        )
        if not (vertical or horizontal):
            raise ValidationError("Only exactly adjacent rectangles with a rectangular union can be merged.")
        page = revisions[0].region.source_page
        if page.original_crop_box is None:
            raise ValidationError("Inspected original source geometry is required for regions.")
        bounds = [
            min(first[0], second[0]),
            min(first[1], second[1]),
            max(first[2], second[2]),
            max(first[3], second[3]),
        ]
        region = m.PageRegion.objects.using(using).create(source_page=page)
        return append_region(region.pk, expected_number=0, bounds_points=bounds, using=using)
