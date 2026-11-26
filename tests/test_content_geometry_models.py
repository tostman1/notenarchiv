"""Immutable revisions retain geometry without granting musical eligibility."""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError

from apps.archive import models as m
from apps.archive import services as s
from apps.archive.content_geometry_services import append_region, source_document
from tests.archive_fixtures import PAGE


def page(*, original=True):
    folder = m.SourceFolder.objects.create(relative_path="Synthetic geometry")
    version, _ = s.observe_version(
        folder.pk,
        "Synthetic geometry/input.pdf",
        sha256="a" * 64,
        byte_size=100,
        pdf_state="UNCHECKED",
    )
    s.record_validation(
        version.pk,
        expected_revision=version.revision,
        pdf_state="VALID",
        page_info=[PAGE],
        original_crop_boxes=[PAGE["crop_box"]] if original else None,
    )
    return version.pages.get()


@pytest.mark.django_db
def test_region_and_logical_revision_history():
    source = page()
    identity = m.PageRegion.objects.create(source_page=source)
    bounds = source.effective_crop_box
    first = m.PageRegionRevision.objects.create(
        region=identity, number=1, bounds_points=bounds, page_fingerprint=source.geometry_fingerprint
    )
    second = m.PageRegionRevision.objects.create(
        region=identity,
        number=2,
        bounds_points=[bounds[0], bounds[1], bounds[2] / 2, bounds[3]],
        page_fingerprint=source.geometry_fingerprint,
    )
    logical = m.LogicalPage.objects.create()
    old = m.LogicalPageRevision.objects.create(logical_page=logical, number=1, region_revision=first)
    new = m.LogicalPageRevision.objects.create(logical_page=logical, number=2, region_revision=second, orientation=90)
    old.refresh_from_db()
    assert old.region_revision_id == first.pk and new.region_revision_id == second.pk
    assert old.content_bounds_points == first.bounds_points
    first.bounds_points = second.bounds_points
    with pytest.raises(ValidationError, match="immutable"):
        first.save()
    with pytest.raises(ProtectedError):
        m.SourcePage.objects.filter(pk=source.pk).delete()


@pytest.mark.django_db
def test_legacy_unknown_crop_allows_whole_page_but_not_segmentation():
    source = page(original=False)
    logical = m.LogicalPage.objects.create()
    m.LogicalPageRevision.objects.create(logical_page=logical, number=1, source_page=source)
    region = m.PageRegion.objects.create(source_page=source)
    with pytest.raises(ValidationError, match="Original source geometry"):
        m.PageRegionRevision.objects.create(
            region=region,
            number=1,
            bounds_points=source.effective_crop_box,
            page_fingerprint=source.geometry_fingerprint,
        )


@pytest.mark.django_db
@pytest.mark.parametrize("bounds", [[0, 0, float("nan"), 10], [-1, 0, 10, 10], [10, 0, 0, 10]])
def test_invalid_regions_fail_closed(bounds):
    source = page()
    region = m.PageRegion.objects.create(source_page=source)
    with pytest.raises(ValidationError):
        m.PageRegionRevision.objects.create(
            region=region, number=1, bounds_points=bounds, page_fingerprint=source.geometry_fingerprint
        )


@pytest.mark.django_db
def test_document_bridge_and_stale_geometry_append():
    source = page()
    document = source_document(source.source_version.source_file_id)
    assert source_document(source.source_version.source_file_id).pk == document.pk
    region = m.PageRegion.objects.create(source_page=source)
    first = append_region(region.pk, expected_number=0, bounds_points=source.effective_crop_box)
    with pytest.raises(s.ArchiveConflict):
        append_region(region.pk, expected_number=0, bounds_points=source.effective_crop_box)
    assert region.revisions.count() == 1 and first.number == 1
    with pytest.raises(IntegrityError, match="immutable content history"), transaction.atomic():
        m.PageRegionRevision.objects.filter(pk=first.pk).update(number=9)
    with pytest.raises(IntegrityError, match="immutable content history"), transaction.atomic():
        m.PageRegionRevision.objects.filter(pk=first.pk).delete()


@pytest.mark.django_db
def test_logical_append_rejects_stale_and_non_integer_revision():
    from apps.archive.content_geometry_services import append_logical_page

    source = page()
    logical = m.LogicalPage.objects.create()
    with pytest.raises(s.ArchiveConflict):
        append_logical_page(logical.pk, expected_number=False, source_page_id=source.pk)
    first = append_logical_page(logical.pk, expected_number=0, source_page_id=source.pk)
    with pytest.raises(s.ArchiveConflict):
        append_logical_page(logical.pk, expected_number=0, source_page_id=source.pk, orientation=90)
    second = append_logical_page(logical.pk, expected_number=1, source_page_id=source.pk, orientation=90)
    assert second.number == 2 and second.orientation == 90
    first.refresh_from_db()
    assert first.number == 1 and first.orientation == 0
