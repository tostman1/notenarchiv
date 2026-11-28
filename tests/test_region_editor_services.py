"""Explicit rectangle edits preserve history and never approve music."""

from types import SimpleNamespace

import pytest
from django.core.exceptions import ValidationError

from apps.archive import models as m
from apps.archive import region_editor_services as editor
from apps.archive.services import ArchiveConflict, observe_version, record_validation, register_base
from tests.archive_fixtures import PAGE
from tests.test_archive_workflow import receipt
from tests.test_content_geometry_models import page
from tests.test_preview import preview  # noqa: F401


@pytest.mark.django_db
def test_browser_region_fixture_records_exact_geometry_before_publication():
    folder = m.SourceFolder.objects.create(relative_path="Synthetic browser geometry")
    version, _ = observe_version(
        folder.pk,
        "Synthetic browser geometry/music.pdf",
        sha256="7" * 64,
        byte_size=100,
        pdf_state="UNCHECKED",
    )
    assert not m.SourcePage.objects.filter(source_version=version).exists()
    version = record_validation(
        version.pk,
        expected_revision=version.revision,
        pdf_state="VALID",
        page_info=[PAGE, PAGE],
        original_crop_boxes=[PAGE["crop_box"], PAGE["crop_box"]],
    )
    file = register_base(version.pk, "_Ungeprueft/browser-geometry.pdf")
    pages = list(m.SourcePage.objects.filter(source_version_id=file.source_version_id).order_by("page_index"))
    assert len(pages) == 2
    assert all(source.original_crop_box == PAGE["crop_box"] for source in pages)


@pytest.fixture
def editable(monkeypatch):
    source = page()
    file = register_base(source.source_version_id, "synthetic.pdf")
    file, _operation = receipt(file)
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


@pytest.mark.django_db
@pytest.mark.parametrize("health", ["MISSING", "CORRUPT"])
def test_health_change_after_verified_read_rejects_under_writer_lock(editable, monkeypatch, health):
    revision = editable.file.revision

    def verified_then_unavailable(file):
        m.ArchiveFile.objects.filter(pk=file.pk).update(publication_state=health)
        return b"verified synthetic bytes"

    monkeypatch.setattr(editor, "preview_bytes", verified_then_unavailable)
    with pytest.raises(ValidationError, match="became unavailable"):
        save(editable)
    editable.file.refresh_from_db()
    assert editable.file.revision == revision and editable.file.publication_state == health
    assert m.PageRegion.objects.count() == m.PageRegionRevision.objects.count() == 0


def test_huge_ocr_selection_integer_rejects_before_float_conversion():
    from apps.archive.ocr_services import validate

    with pytest.raises(ValueError, match="rectangle"):
        validate(
            {"file_id": "00000000-0000-0000-0000-000000000001", "selection": {"page": 0, "box": [0, 0, 10**400, 1]}}
        )


def test_authenticated_graphical_region_save_has_explicit_pins_and_no_approval(preview, client, monkeypatch):  # noqa: F811
    from django.urls import reverse

    file, _data, _target = preview
    url = reverse("archive_review_detail", args=[file.pk])
    response = client.get(url)
    assert response.status_code == 200
    assert b'value="region_save"' in response.content
    captured = []
    monkeypatch.setattr(editor, "save_rectangle", lambda *a, **kw: captured.append((a, kw)))
    response = client.post(
        url,
        {
            "action": "region_save",
            "expected_file_revision": file.revision,
            "source_version_id": str(file.source_version_id),
            "expected_region_number": 0,
            "page": 1,
            "left": 10,
            "top": 20,
            "right": 80,
            "bottom": 90,
        },
    )
    assert response.status_code == 302
    assert captured[0][1]["selection"] == {"page": 0, "box": [0.1, 0.2, 0.8, 0.9]}
    assert captured[0][1]["expected_file_revision"] == file.revision
    assert m.ReviewInspection.objects.count() == m.ContentConfirmation.objects.count() == 0
    assert m.ArchiveFile.objects.get(pk=file.pk).current_proposal_id is None


@pytest.mark.parametrize("error", [FileNotFoundError, PermissionError])
def test_region_save_handles_raw_unavailable_read(preview, client, monkeypatch, error):  # noqa: F811
    from django.urls import reverse

    file, _data, _target = preview
    url = reverse("archive_review_detail", args=[file.pk])

    def unavailable(*args, **kwargs):
        raise error("synthetic unavailable CLEAN")

    monkeypatch.setattr(editor, "save_rectangle", unavailable)
    response = client.post(
        url,
        {
            "action": "region_save",
            "expected_file_revision": file.revision,
            "source_version_id": str(file.source_version_id),
            "expected_region_number": 0,
            "page": 1,
            "left": 10,
            "top": 20,
            "right": 80,
            "bottom": 90,
        },
        follow=True,
    )
    assert response.status_code == 200
    assert "Bereich nicht gespeichert" in response.content.decode()
    assert m.PageRegion.objects.count() == m.PageRegionRevision.objects.count() == 0
    assert m.ReviewInspection.objects.count() == m.ContentConfirmation.objects.count() == 0


def test_review_lists_latest_region_only_without_workflow_mutation(preview, client):  # noqa: F811
    from django.urls import reverse

    from core.page_geometry import PageGeometry

    file, _data, _target = preview
    source = file.source_version.pages.get()
    # The synthetic preview fixture intentionally stores legacy page metadata;
    # use existing exact-geometry fixture for an independent source publication.
    exact = page()
    other = register_base(exact.source_version_id, "exact.pdf")
    region = m.PageRegion.objects.create(source_page=exact)
    first = m.PageRegionRevision.objects.create(
        region=region,
        number=1,
        bounds_points=PageGeometry(exact.media_box, exact.original_crop_box).effective_points,
        page_fingerprint=exact.geometry_fingerprint,
    )
    second = m.PageRegionRevision.objects.create(
        region=region,
        number=2,
        bounds_points=[0, 0, 100, 200],
        page_fingerprint=exact.geometry_fingerprint,
    )
    response = client.get(reverse("archive_review_detail", args=[other.pk]))
    assert response.status_code == 200
    assert [item.pk for item in response.context["regions"]] == [second.pk]
    assert f'data-region-id="{region.pk}"' in response.content.decode()
    assert 'data-region-number="2"' in response.content.decode()
    assert first.pk != second.pk and source.source_version_id == file.source_version_id
    assert m.ReviewInspection.objects.count() == m.ContentConfirmation.objects.count() == 0
