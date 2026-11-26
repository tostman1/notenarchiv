"""Short SQLite-serialized append operations for stable geometry identities."""

from uuid import UUID, uuid5

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F

from apps.archive import models as m
from apps.archive.services import ArchiveConflict

DOCUMENT_NAMESPACE = UUID("0ec6afc5-f96f-4e47-905a-3650b59e9411")


def source_document(source_file_id, *, using="default"):
    """Idempotent identity bridge, also for newly indexed sources."""
    with transaction.atomic(using=using):
        if not m.SourceFile.objects.using(using).filter(pk=source_file_id).update(revision=F("revision")):
            raise ValidationError("Source file does not exist.")
        document, _ = m.SourceDocument.objects.using(using).get_or_create(
            source_file_id=source_file_id, defaults={"id": uuid5(DOCUMENT_NAMESPACE, str(source_file_id))}
        )
        return document


def append_region(region_id, *, expected_number, bounds_points, using="default"):
    """Serialize writers before reading current history; stale callers cannot append."""
    with transaction.atomic(using=using):
        # Acquire the existing SQLite writer lock without changing source identity.
        version_ids = m.PageRegion.objects.using(using).filter(pk=region_id).values("source_page__source_version_id")
        if not m.SourceVersion.objects.using(using).filter(pk__in=version_ids).update(revision=F("revision")):
            raise ValidationError("Region does not exist.")
        region = m.PageRegion.objects.using(using).select_related("source_page").get(pk=region_id)
        latest = region.revisions.using(using).order_by("-number").first()
        current = latest.number if latest else 0
        if type(expected_number) is not int or expected_number != current:
            raise ArchiveConflict()
        return m.PageRegionRevision.objects.using(using).create(
            region=region,
            number=current + 1,
            bounds_points=bounds_points,
            page_fingerprint=region.source_page.geometry_fingerprint,
        )


def append_logical_page(
    logical_page_id,
    *,
    expected_number,
    source_page_id=None,
    region_revision_id=None,
    orientation=0,
    content_bounds_points=None,
    using="default",
):
    """Append an exact input revision under the same SQLite writer boundary."""
    with transaction.atomic(using=using):
        # Stable identities themselves are immutable. Lock the owning source row
        # before reading revision history, including a previously empty identity.
        source_ids = (
            m.SourcePage.objects.using(using).filter(pk=source_page_id).values("source_version_id")
            if source_page_id is not None
            else m.PageRegionRevision.objects.using(using)
            .filter(pk=region_revision_id)
            .values("region__source_page__source_version_id")
        )
        if not m.SourceVersion.objects.using(using).filter(pk__in=source_ids).update(revision=F("revision")):
            raise ValidationError("Logical source input does not exist.")
        logical = m.LogicalPage.objects.using(using).filter(pk=logical_page_id).first()
        if logical is None:
            raise ValidationError("Logical page does not exist.")
        latest = logical.revisions.using(using).order_by("-number").first()
        current = latest.number if latest else 0
        if type(expected_number) is not int or expected_number != current:
            raise ArchiveConflict()
        return m.LogicalPageRevision.objects.using(using).create(
            logical_page=logical,
            number=current + 1,
            source_page_id=source_page_id,
            region_revision_id=region_revision_id,
            orientation=orientation,
            content_bounds_points=content_bounds_points,
        )
