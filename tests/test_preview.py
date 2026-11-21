"""WP-18 access boundary, immutable CLEAN bytes and bounded native thumbnails."""

import uuid
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.archive import models as m
from apps.archive import preview_services
from core.locking import ProcessLock
from core.pdf.types import PdfError
from tests.test_archive_workflow import confirm, draft, receipt
from tests.test_archive_workflow import reviewed_inputs as reviewed_fixture

reviewed_inputs = reviewed_fixture


@pytest.fixture
def preview(archive, settings, tmp_path, client):
    _folder, _version, file, data = archive
    file, _operation = receipt(file)
    settings.CURATED_DIR = tmp_path / "clean"
    target = settings.CURATED_DIR / file.relative_path
    target.parent.mkdir(parents=True)
    target.write_bytes(data)
    settings.DIAGNOSTIC_LOG_DIR = tmp_path / "logs"
    actor = get_user_model().objects.create_user("preview-archivist", password="Synthetic-preview-135")
    client.force_login(actor)
    return file, data, target


def url(file, endpoint="viewer", **kwargs):
    return reverse("archive_preview:" + endpoint, kwargs={"file_id": file.pk, **kwargs})


@pytest.mark.parametrize("endpoint,kwargs", [("viewer", {}), ("document", {}), ("thumbnail", {"page": 1})])
def test_anonymous_preview_requires_login(preview, client, endpoint, kwargs):
    file, _data, _target = preview
    client.logout()
    response = client.get(url(file, endpoint, **kwargs))
    assert response.status_code == 302 and response.url.startswith("/login/?next=")


def test_pending_clean_document_is_exact_private_attachment(preview, client):
    file, data, target = preview
    before = (m.ReviewInspection.objects.count(), m.AuditEvent.objects.count(), file.revision)
    viewer = client.get(url(file))
    assert viewer.status_code == 200 and "Ungeprüfte Version" in viewer.content.decode()
    response = client.get(url(file, "document"))
    assert response.status_code == 200 and response.content == data == target.read_bytes()
    assert response["Content-Type"] == "application/pdf"
    assert response["Content-Disposition"].startswith("attachment;")
    assert response["Content-Security-Policy"] == "sandbox; default-src 'none'"
    assert response["Cache-Control"] == "private, no-store"
    assert response["Cross-Origin-Resource-Policy"] == "same-origin"
    file.refresh_from_db()
    assert before == (m.ReviewInspection.objects.count(), m.AuditEvent.objects.count(), file.revision)
    assert not m.ArchiveFile.objects.usable().exists()


def test_confirmed_clean_preview_preserves_review_and_bytes(reviewed_inputs, settings, tmp_path, client):
    _folder, _version, file, actor, _other, arrangement, parts = reviewed_inputs
    file = confirm(file, draft(file, actor, arrangement, parts[:1]), actor)
    from tests.pdf_fixtures import pdf

    data = pdf()
    settings.CURATED_DIR = tmp_path
    target = tmp_path / file.relative_path
    target.parent.mkdir(parents=True)
    target.write_bytes(data)
    client.force_login(actor)
    assert "Bestätigte Version" in client.get(url(file)).content.decode()
    assert client.get(url(file, "document")).content == data
    assert m.ReviewInspection.objects.count() == 1
    assert m.ArchiveFile.objects.usable().get().pk == file.pk


@pytest.mark.parametrize("path", ["../secret.pdf", "/secret.pdf", "C:/secret.pdf", "x\\secret.pdf", ".staging/x.pdf"])
def test_tampered_database_path_fails_closed(preview, client, path):
    file, _data, _target = preview
    m.ArchiveFile.objects.filter(pk=file.pk).update(relative_path=path)
    assert client.get(url(file, "document")).status_code == 404


def test_corrupt_missing_and_oversize_clean_fail_without_path_disclosure(preview, client, settings):
    file, _data, target = preview
    target.write_bytes(b"not the approved hash")
    response = client.get(url(file, "document"))
    assert response.status_code == 404 and str(target).encode() not in response.content
    target.unlink()
    assert client.get(url(file, "document")).status_code == 404
    settings.PDF_MAX_BYTES = 1024
    assert client.get(url(file, "document")).status_code == 404


@pytest.mark.parametrize("state", ["UNPUBLISHED", "MISSING", "CORRUPT"])
def test_unavailable_publication_is_denied(preview, client, state):
    file, _data, _target = preview
    m.ArchiveFile.objects.filter(pk=file.pk).update(publication_state=state)
    assert client.get(url(file)).status_code == 404


@pytest.mark.parametrize("state", ["REJECTED", "WITHDRAWN"])
def test_rejected_or_withdrawn_preview_is_denied(preview, client, state):
    file, _data, _target = preview
    m.ArchiveFile.objects.filter(pk=file.pk).update(review_state=state)
    assert client.get(url(file, "document")).status_code == 404


def test_unknown_source_and_path_ids_are_not_archive_preview_ids(preview, client):
    file, _data, _target = preview
    for identifier in (uuid.uuid4(), file.source_version_id, file.source_version.source_file_id):
        assert client.get(reverse("archive_preview:document", kwargs={"file_id": identifier})).status_code == 404
    for path in ("../../secret", "%2e%2e/secret", "C:/secret.pdf"):
        assert client.get("/archive/preview/" + path + "/document/").status_code == 404
    assert client.post(url(file, "document")).status_code in {403, 405}


def test_real_thumbnail_is_bounded_and_scratch_is_cleaned(preview, client):
    file, _data, target = preview
    response = client.get(url(file, "thumbnail", page=1))
    assert response.status_code == 200 and response["Content-Type"] == "image/png"
    import struct

    width, height = struct.unpack(">II", response.content[16:24])
    assert max(width, height) <= 256 and len(response.content) <= 1_048_576
    scratch = target.parents[1].parent / "preview-scratch"
    assert not list(scratch.iterdir())
    assert client.get(url(file, "thumbnail", page=0)).status_code == 404
    assert client.get(url(file, "thumbnail", page=2)).status_code == 404


def test_native_failure_is_sanitized(preview, client, monkeypatch):
    file, _data, _target = preview

    def failure(*args):
        raise PdfError("TIMEOUT")

    monkeypatch.setattr(preview_services, "thumbnail", failure)
    response = client.get(url(file, "thumbnail", page=1))
    assert response.status_code == 404 and b"TIMEOUT" not in response.content


def test_busy_thumbnail_is_bounded_and_fails_safely(preview, client, settings):
    file, _data, _target = preview
    with ProcessLock(Path(settings.DIAGNOSTIC_LOG_DIR).parent / "preview-render.lock"):
        response = client.get(url(file, "thumbnail", page=1))
    assert response.status_code == 404 and b"lock" not in response.content


def test_forged_receipt_and_invalid_pdf_validation_are_denied(preview, client):
    file, _data, _target = preview
    operation = file.publication_operation
    intent = operation.intent
    type(intent).objects.filter(pk=intent.pk).update(result={"sha256": file.sha256})
    assert client.get(url(file)).status_code == 404
    type(intent).objects.filter(pk=intent.pk).update(result=operation.expected_receipt)
    m.SourceVersion.objects.filter(pk=file.source_version_id).update(pdf_state="INVALID")
    assert client.get(url(file, "document")).status_code == 404


@pytest.mark.skipif(__import__("os").name != "posix", reason="Actual descriptor/symlink boundary requires POSIX")
def test_symlink_final_and_parent_are_denied(preview, client, tmp_path):
    file, data, target = preview
    outside = tmp_path / "outside.pdf"
    outside.write_bytes(data)
    target.unlink()
    target.symlink_to(outside)
    assert client.get(url(file, "document")).status_code == 404
    target.unlink()
    parent = target.parent
    parent.rmdir()
    parent.symlink_to(tmp_path, target_is_directory=True)
    assert client.get(url(file, "document")).status_code == 404


def test_pdfjs_assets_are_pinned_local_and_viewer_has_no_active_layers():
    import hashlib
    import json

    root = Path("static/vendor/pdfjs")
    for name, digest in json.loads(root.joinpath("SHA256.json").read_text()).items():
        assert hashlib.sha256(root.joinpath(name).read_bytes()).hexdigest() == digest
    assert root.joinpath("LICENSE").is_file()
    assert b"6.5.438" in root.joinpath("build/pdf.mjs").read_bytes()
    script = Path("static/archive/preview.mjs").read_text()
    assert "isEvalSupported: false" in script and "enableXfa: false" in script
    assert "https://" not in script and "http://" not in script
