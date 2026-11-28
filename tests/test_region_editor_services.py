"""Explicit rectangle edits preserve history and never approve music."""

from types import SimpleNamespace

import pytest
from django.core.exceptions import ValidationError

from apps.archive import models as m
from apps.archive import region_editor_services as editor
from apps.archive.services import ArchiveConflict, register_base
from tests.test_content_geometry_models import page


@pytest.fixture
def editable(monkeypatch):
    source = page()
    file = register_base(source.source_version_id, "synthetic.pdf")
    monkeypatch.setattr(editor, "preview_file", lambda *a, **kw: file)
    monkeypatch.setattr(editor, "preview_bytes", lambda file: b"verified synthetic bytes")
    return SimpleNamespace(file=file, page=source)


def save(item, **kwargs):
    values = {
        "expected_file_revision": item.file.revision,
        "source_version_id": item.file.source_version_id,
        "selection": {"page": 0, "box": [0, 0, 0.5, 1]},
    }
    values.update(kwargs)
    return editor.save_rectangle(item.file.pk, **values)


@pytest.mark.django_db
def test_explicit_region_edit_preserves_pinned_history_without_approval(editable):
    first = save(editable)
    logical = m.LogicalPage.objects.create()
    pinned = m.LogicalPageRevision.objects.create(logical_page=logical, number=1, region_revision=first)
    second = save(
        editable,
        region_id=first.region_id,
        expected_region_number=1,
        selection={"page": 0, "box": [0.5, 0, 1, 1]},
    )
    assert second.region_id == first.region_id and second.number == 2
    first.refresh_from_db()
    pinned.refresh_from_db()
    assert pinned.region_revision_id == first.pk and first.bounds_points != second.bounds_points
    editable.file.refresh_from_db()
    assert editable.file.current_proposal_id is None
    assert m.ContentInspection.objects.count() == m.ContentConfirmation.objects.count() == 0
    assert m.ReviewInspection.objects.count() == 0


@pytest.mark.django_db
def test_stale_region_and_file_reject_without_new_history(editable):
    first = save(editable)
    with pytest.raises(ArchiveConflict):
        save(editable, region_id=first.region_id, expected_region_number=0)
    with pytest.raises(ArchiveConflict):
        save(editable, expected_file_revision=editable.file.revision + 1)
    with pytest.raises(ArchiveConflict):
        save(editable, source_version_id=first.pk)
    assert m.PageRegion.objects.count() == m.PageRegionRevision.objects.count() == 1


@pytest.mark.django_db
def test_cross_page_region_and_unavailable_geometry_fail_closed(editable):
    from apps.archive import services
    from tests.archive_fixtures import PAGE

    folder = m.SourceFolder.objects.create(relative_path="Synthetic foreign geometry")
    version, _ = services.observe_version(
        folder.pk, "Synthetic foreign geometry/input.pdf", sha256="b" * 64, byte_size=100, pdf_state="UNCHECKED"
    )
    services.record_validation(
        version.pk,
        expected_revision=version.revision,
        pdf_state="VALID",
        page_info=[PAGE],
        original_crop_boxes=[PAGE["crop_box"]],
    )
    foreign = m.PageRegion.objects.create(source_page=version.pages.get())
    with pytest.raises(ValidationError, match="does not belong"):
        save(editable, region_id=foreign.pk)
    with pytest.raises(ValidationError, match="geometry"):
        save(editable, selection={"page": 1, "box": [0, 0, 1, 1]})
    assert m.PageRegionRevision.objects.count() == 0


@pytest.mark.django_db
def test_missing_verified_bytes_never_creates_geometry(editable, monkeypatch):
    def unavailable(file):
        raise ValidationError("Unavailable source")

    monkeypatch.setattr(editor, "preview_bytes", unavailable)
    with pytest.raises(ValidationError, match="Unavailable"):
        save(editable)
    assert m.PageRegion.objects.count() == m.PageRegionRevision.objects.count() == 0


def test_huge_ocr_selection_integer_rejects_before_float_conversion():
    from apps.archive.ocr_services import validate

    with pytest.raises(ValueError, match="rectangle"):
        validate(
            {"file_id": "00000000-0000-0000-0000-000000000001", "selection": {"page": 0, "box": [0, 0, 10**400, 1]}}
        )
