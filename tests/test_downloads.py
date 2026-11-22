"""Direct unchanged PDFs and bounded ZIPs, no project/member/RAW mutations."""

import io
import zipfile

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import Client
from django.urls import reverse

from apps.archive import download_services as s
from apps.archive import models as m
from apps.archive import services as archive
from core import downloads
from core.files import FileError
from core.locking import ProcessLock


@pytest.fixture
def download_inputs(edition_inputs, settings, tmp_path, client):
    settings.DIAGNOSTIC_LOG_DIR = tmp_path / "data" / "logs"
    settings.DIAGNOSTIC_LOG_DIR.parent.mkdir()
    client.force_login(edition_inputs[0])
    return edition_inputs


def content(response):
    try:
        return b"".join(response.streaming_content)
    finally:
        response.close()


def test_direct_pdf_unchanged_format_and_no_project_dependency(download_inputs, client, settings):
    _actor, _arr, _parts, first, _second, _make = download_inputs
    path = settings.CURATED_DIR / first.relative_path
    before = path.read_bytes(), path.stat().st_mtime_ns
    response = client.get(reverse("archive_note_download", args=[first.pk]))
    assert response.status_code == 200 and response["Content-Type"] == "application/pdf"
    assert "attachment" in response["Content-Disposition"] and "no-store" in response["Cache-Control"]
    assert content(response) == before[0]
    assert (path.read_bytes(), path.stat().st_mtime_ns) == before
    assert not list((settings.DIAGNOSTIC_LOG_DIR.parent / "download-scratch").iterdir())
    from apps.members.models import Member

    assert Member.objects.count() == 0


def test_multiple_selection_zip_bytes_order_and_actor_bound_token(download_inputs, client, settings):
    actor, _arr, _parts, first, second, _make = download_inputs
    response = client.post(reverse("archive_note_selection"), {"file": [str(second.pk), str(first.pk)]})
    assert response.status_code == 200 and "ZIP herunterladen" in response.content.decode()
    token = response.context["token"]
    other = get_user_model().objects.create_user("synthetic-download-other")
    with pytest.raises(s.SelectionChanged):
        s.from_token(token, other)
    response = client.post(reverse("archive_note_selection_download"), {"token": token})
    assert response.status_code == 200
    with zipfile.ZipFile(io.BytesIO(content(response))) as zipped:
        assert zipped.namelist() == [f"note-{file.pk}.pdf" for file in (second, first)]
        for file in (second, first):
            assert zipped.read(f"note-{file.pk}.pdf") == (settings.CURATED_DIR / file.relative_path).read_bytes()
            assert zipped.getinfo(f"note-{file.pk}.pdf").compress_type == zipfile.ZIP_STORED
    assert actor.is_active


@pytest.mark.parametrize("status", ["PENDING", "WITHDRAWN", "MISSING", "CORRUPT"])
def test_ineligible_selected_notes_are_not_downloadable(download_inputs, client, status):
    actor, _arr, _parts, first, _second, _make = download_inputs
    if status == "WITHDRAWN":
        archive.withdraw(first.pk, actor=actor, expected_revision=first.revision)
    elif status == "PENDING":
        m.ArchiveFile.objects.filter(pk=first.pk).update(review_state=status)
    else:
        m.ArchiveFile.objects.filter(pk=first.pk).update(publication_state=status)
    assert client.get(reverse("archive_note_download", args=[first.pk])).status_code == 400
    assert client.post(reverse("archive_note_selection"), {"file": [str(first.pk)]}).status_code == 400


def test_hash_corruption_tampering_stale_selection_and_duplicate_denied(download_inputs, client, settings):
    actor, _arr, _parts, first, _second, _make = download_inputs
    token = s.selection_token(s.files([first.pk]), actor)
    assert client.post(reverse("archive_note_selection_download"), {"token": "tampered"}).status_code == 409
    with pytest.raises(ValidationError):
        s.files([first.pk, first.pk])
    assert client.post(reverse("archive_note_selection"), {"file": []}).status_code == 400
    assert client.post(reverse("archive_note_selection"), {"file": ["../escape"]}).status_code == 400
    (settings.CURATED_DIR / first.relative_path).write_bytes(b"synthetic corruption")
    assert client.get(reverse("archive_note_download", args=[first.pk])).status_code == 400
    m.ArchiveFile.objects.filter(pk=first.pk).update(revision=first.revision + 1)
    assert client.post(reverse("archive_note_selection_download"), {"token": token}).status_code == 409


def test_auth_csrf_and_download_lock_remain_active(download_inputs, client, settings):
    actor, _arr, _parts, first, _second, _make = download_inputs
    csrf = Client(enforce_csrf_checks=True)
    csrf.force_login(actor)
    assert csrf.post(reverse("archive_note_selection"), {"file": [str(first.pk)]}).status_code == 403
    client.logout()
    assert client.get(reverse("archive_note_download", args=[first.pk])).status_code == 302
    client.force_login(actor)
    with ProcessLock(settings.DIAGNOSTIC_LOG_DIR.parent / "direct-download.lock"):
        assert client.get(reverse("archive_note_download", args=[first.pk])).status_code == 400


def test_response_reads_verified_stage_not_mutable_archive(download_inputs, client, settings):
    _actor, _arr, _parts, first, _second, _make = download_inputs
    path = settings.CURATED_DIR / first.relative_path
    before = path.read_bytes()
    response = client.get(reverse("archive_note_download", args=[first.pk]))
    assert response.status_code == 200
    path.write_bytes(b"changed after valid response preparation")
    assert content(response) == before
    # Response closure releases the lock and removes all private temporaries.
    with ProcessLock(settings.DIAGNOSTIC_LOG_DIR.parent / "direct-download.lock"):
        pass


def test_download_limits_and_unconfirmed_derivative(download_inputs, tmp_path):
    _actor, _arr, _parts, first, _second, make = download_inputs
    with pytest.raises(ValidationError):
        s.files([first.pk] * 21)
    invalid = downloads.Input(tmp_path, "x.pdf", "a" * 64, downloads.MAX_TOTAL + 1, "x.pdf")
    with pytest.raises(FileError):
        downloads.build([invalid], tmp_path, zipped=True)
    derivative = make(5, derivative=True)
    selected = s.files([derivative.pk])
    stream = s.stage(selected, zipped=False)
    try:
        assert stream.read().startswith(b"%PDF")
    finally:
        stream.close()


def test_combined_parts_download_once_and_preserve_a3_a4(download_inputs, settings):
    import hashlib

    from tests.archive_fixtures import PAGE
    from tests.pdf_fixtures import A3, A4, pdf

    actor, arr, parts, first, _second, _make = download_inputs
    version, _ = archive.observe_version(
        first.source_version.source_file.folder_id,
        "Synthetic editions/combined.pdf",
        sha256=hashlib.sha256(data := pdf(sizes=(A3, A4))).hexdigest(),
        byte_size=len(data),
        pdf_state="VALID",
        page_info=[
            {**PAGE, "media_box": [0, 0, *A3], "crop_box": [0, 0, *A3], "width_points": A3[0], "height_points": A3[1]},
            PAGE,
        ],
    )
    other = parts[0].__class__.objects.create(instrument=parts[0].instrument, code="3")
    from tests.test_archive_workflow import confirm, draft, receipt

    file, _ = receipt(archive.register_base(version.pk, "_Ungeprueft/combined.pdf"))
    file = confirm(file, draft(file, actor, arr, [parts[0], other]), actor, path="Synthetic editions/combined.pdf")
    path = settings.CURATED_DIR / file.relative_path
    path.write_bytes(data)
    assert file.assignments.usable().count() == 2
    stream = s.stage(s.files([file.pk]), zipped=True)
    try:
        with zipfile.ZipFile(stream) as zipped:
            assert len(zipped.namelist()) == 1
            assert zipped.read(zipped.namelist()[0]) == data
    finally:
        stream.close()


def test_withdrawal_during_stage_denied_and_temporaries_removed(download_inputs, settings, monkeypatch):
    actor, _arr, _parts, first, _second, _make = download_inputs
    original = downloads.build

    def withdraw(*args, **kwargs):
        stream = original(*args, **kwargs)
        archive.withdraw(first.pk, actor=actor, expected_revision=first.revision)
        return stream

    monkeypatch.setattr(downloads, "build", withdraw)
    with pytest.raises(ValidationError):
        s.stage(s.files([first.pk]), zipped=False)
    assert not list((settings.DIAGNOSTIC_LOG_DIR.parent / "download-scratch").iterdir())
    with ProcessLock(settings.DIAGNOSTIC_LOG_DIR.parent / "direct-download.lock"):
        pass


def test_derivative_preview_requires_own_confirmation(download_inputs, client):
    _actor, _arr, _parts, _first, _second, make = download_inputs
    derivative = make(5, derivative=True)
    assert client.get(reverse("archive_preview:document", args=[derivative.pk])).status_code == 200
    m.ArchiveFile.objects.filter(pk=derivative.pk).update(review_state="PENDING")
    assert client.get(reverse("archive_preview:document", args=[derivative.pk])).status_code == 404


def test_response_close_releases_single_download_slot(download_inputs, settings):
    first = download_inputs[3]
    stream = s.stage(s.files([first.pk]), zipped=False)
    assert not hasattr(stream, "fileno")
    with pytest.raises(OSError):
        s.stage(s.files([first.pk]), zipped=False)
    stream.close()
    stream.close()
    with ProcessLock(settings.DIAGNOSTIC_LOG_DIR.parent / "direct-download.lock"):
        pass


@pytest.mark.skipif(__import__("os").name != "posix", reason="POSIX symlink boundary")
def test_symlink_source_or_scratch_never_followed(download_inputs, settings, tmp_path):
    first = download_inputs[3]
    path = settings.CURATED_DIR / first.relative_path
    external = tmp_path / "external.pdf"
    external.write_bytes(path.read_bytes())
    path.unlink()
    path.symlink_to(external)
    with pytest.raises(FileError):
        s.stage(s.files([first.pk]), zipped=False)


def test_expired_selection_and_response_timeout_never_retry(download_inputs, monkeypatch):
    actor, _arr, _parts, first, _second, _make = download_inputs
    token = s.selection_token(s.files([first.pk]), actor)
    from django.core import signing

    def expired(*args, **kwargs):
        raise signing.SignatureExpired("synthetic expiry")

    monkeypatch.setattr(s.signing, "loads", expired)
    with pytest.raises(s.SelectionChanged):
        s.from_token(token, actor)
    stream = s.stage(s.files([first.pk]), zipped=False)
    stream.deadline = 0
    assert stream.read(1024) == b"" and stream.stream.closed


@pytest.mark.skipif(__import__("os").name != "posix", reason="POSIX scratch no-follow")
def test_scratch_symlink_rejected_without_external_writes(download_inputs, settings, tmp_path):
    target = tmp_path / "outside"
    target.mkdir()
    (settings.DIAGNOSTIC_LOG_DIR.parent / "download-scratch").symlink_to(target, target_is_directory=True)
    with pytest.raises(FileError):
        s.stage(s.files([download_inputs[3].pk]), zipped=False)
    assert not list(target.iterdir())


def test_copy_change_or_staging_failure_closes_stream(download_inputs, settings, monkeypatch):
    selected = s.files([download_inputs[3].pk])
    original = downloads.copy_snapshot

    def fail(*args, **kwargs):
        original(*args, **kwargs)
        raise FileError("CONTENT_CHANGED")

    monkeypatch.setattr(downloads, "copy_snapshot", fail)
    with pytest.raises(FileError):
        s.stage(selected, zipped=True)
    assert not list((settings.DIAGNOSTIC_LOG_DIR.parent / "download-scratch").iterdir())
    with ProcessLock(settings.DIAGNOSTIC_LOG_DIR.parent / "direct-download.lock"):
        pass
