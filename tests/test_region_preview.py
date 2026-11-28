"""Saved unconfirmed revisions remain private, exact and read-only previews."""

import hashlib

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.archive import models as m
from apps.archive.services import observe_version, record_validation, register_base
from tests.archive_fixtures import PAGE
from tests.pdf_fixtures import A4, pdf
from tests.test_archive_workflow import receipt


@pytest.fixture
def region_preview(settings, tmp_path, client):
    settings.CURATED_DIR = tmp_path / "clean"
    settings.CURATED_DIR.mkdir()
    settings.DIAGNOSTIC_LOG_DIR = tmp_path / "private" / "logs"
    settings.DIAGNOSTIC_LOG_DIR.parent.mkdir()
    data = pdf(sizes=(A4,))
    folder = m.SourceFolder.objects.create(relative_path="Synthetic region preview")
    version, _ = observe_version(
        folder.pk,
        "Synthetic region preview/music.pdf",
        sha256=hashlib.sha256(data).hexdigest(),
        byte_size=len(data),
        pdf_state="UNCHECKED",
    )
    version = record_validation(
        version.pk,
        expected_revision=version.revision,
        pdf_state="VALID",
        page_info=[PAGE],
        original_crop_boxes=[PAGE["crop_box"]],
    )
    file, _ = receipt(register_base(version.pk, "preview.pdf"))
    target = settings.CURATED_DIR / file.relative_path
    target.write_bytes(data)
    source = version.pages.get()
    region = m.PageRegion.objects.create(source_page=source)
    revisions = [
        m.PageRegionRevision.objects.create(
            region=region,
            number=number,
            bounds_points=bounds,
            page_fingerprint=source.geometry_fingerprint,
        )
        for number, bounds in enumerate(([0, 0, 100, 200], [100, 0, 200, 200]), 1)
    ]
    client.force_login(get_user_model().objects.create_user("synthetic-region-preview"))
    return file, revisions, target


@pytest.mark.django_db
def test_saved_revision_preview_renders_historical_selection_without_approval(region_preview, client):
    file, revisions, target = region_preview
    original = target.read_bytes()
    for revision in revisions:
        response = client.get(reverse("archive_preview:region_excerpt", args=[file.pk, revision.pk]))
        assert response.status_code == 200
        assert response.content.startswith(b"\x89PNG\r\n\x1a\n")
        assert response["Cache-Control"] == "private, no-store"
        assert response["X-Content-Type-Options"] == "nosniff"
    assert target.read_bytes() == original
    assert m.ContentInspection.objects.count() == m.ContentConfirmation.objects.count() == 0
    assert m.ReviewInspection.objects.count() == 0
    file.refresh_from_db()
    assert file.current_proposal_id is None and file.review_state == "PENDING"


@pytest.mark.django_db
def test_saved_revision_preview_requires_authentication_and_verified_source(region_preview, client):
    file, revisions, target = region_preview
    url = reverse("archive_preview:region_excerpt", args=[file.pk, revisions[0].pk])
    assert client.post(url).status_code == 405
    client.logout()
    assert client.get(url).status_code == 302
    client.force_login(get_user_model().objects.get(username="synthetic-region-preview"))
    target.write_bytes(b"corrupted synthetic source")
    assert client.get(url).status_code == 404


@pytest.mark.django_db
def test_saved_revision_preview_rejects_foreign_version_even_with_identical_hash(region_preview, client):
    file, revisions, _target = region_preview
    folder = m.SourceFolder.objects.create(relative_path="Other synthetic region")
    version, _ = observe_version(
        folder.pk,
        "Other synthetic region/music.pdf",
        sha256=file.sha256,
        byte_size=file.byte_size,
        pdf_state="UNCHECKED",
    )
    version = record_validation(
        version.pk,
        expected_revision=version.revision,
        pdf_state="VALID",
        page_info=[PAGE],
        original_crop_boxes=[PAGE["crop_box"]],
    )
    source = version.pages.get()
    region = m.PageRegion.objects.create(source_page=source)
    foreign = m.PageRegionRevision.objects.create(
        region=region,
        number=1,
        bounds_points=revisions[0].bounds_points,
        page_fingerprint=source.geometry_fingerprint,
    )
    response = client.get(reverse("archive_preview:region_excerpt", args=[file.pk, foreign.pk]))
    assert response.status_code == 404
    assert m.ContentInspection.objects.count() == m.ContentConfirmation.objects.count() == 0
