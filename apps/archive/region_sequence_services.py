"""Explicit region-to-content proposals using the existing revision model."""

from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F

from apps.archive import models as m
from apps.archive.content_geometry_services import append_logical_page
from apps.archive.content_services import propose_content
from apps.archive.preview_services import preview_bytes, preview_file
from apps.archive.services import ArchiveConflict


def propose_region_sequence(
    file_id,
    *,
    edition_id,
    expected_edition_number,
    expected_file_revision,
    source_version_id,
    region_revision_ids,
    using="default",
):
    """Save explicit ordered occurrences, never inspection or musical approval.

    Only current region revisions may start a new proposal. Historical preview
    remains independent. Repeated occurrences pin the same logical revision,
    while existing manifests and historical inputs are never mutated.
    """
    if not isinstance(region_revision_ids, (list, tuple)) or not 1 <= len(region_revision_ids) <= 16:
        raise ValidationError("Select one to sixteen explicit region revisions.")
    try:
        ids = [UUID(str(value)) for value in region_revision_ids]
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValidationError("Region revisions require explicit UUIDs.") from exc
    if type(expected_edition_number) is not int or expected_edition_number < 0:
        raise ValidationError("An explicit edition revision is required.")
    file = preview_file(file_id, using=using)
    if file.kind != "BASE":
        raise ValidationError("Content requires the exact unchanged source publication.")
    preview_bytes(file)
    with transaction.atomic(using=using):
        if not m.ArchiveFile.objects.using(using).filter(pk=file.pk).update(revision=F("revision")):
            raise ArchiveConflict()
        file.refresh_from_db(using=using)
        if (
            type(expected_file_revision) is not int
            or expected_file_revision != file.revision
            or str(source_version_id) != str(file.source_version_id)
            or file.publication_state != "AVAILABLE"
            or file.review_state in ("REJECTED", "WITHDRAWN")
        ):
            raise ArchiveConflict()
        regions = m.PageRegionRevision.objects.using(using).select_related("region__source_page").in_bulk(ids)
        logicals = {}
        for revision_id in dict.fromkeys(ids):
            revision = regions.get(revision_id)
            if revision is None or revision.region.source_page.source_version_id != file.source_version_id:
                raise ValidationError("Region does not belong to the exact source version.")
            page = revision.region.source_page
            if page.original_crop_box is None or revision.page_fingerprint != page.geometry_fingerprint:
                raise ValidationError("Original source geometry is required.")
            latest = revision.region.revisions.using(using).order_by("-number").values_list("pk", flat=True).first()
            if latest != revision.pk:
                raise ArchiveConflict()
            logical = m.LogicalPage.objects.using(using).create()
            logicals[revision_id] = append_logical_page(
                logical.pk, expected_number=0, region_revision_id=revision.pk, using=using
            )
        return propose_content(
            edition_id,
            expected_number=expected_edition_number,
            inputs=[(logicals[revision_id].pk, file.pk) for revision_id in ids],
            using=using,
        )
