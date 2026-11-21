"""Batch auth/version/inspection gates and atomic rollback on any invalid item."""

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import Client
from django.urls import reverse

from apps.archive import models as m
from apps.archive import review_services
from apps.archive import services as s
from apps.archive.batch_review import approve_batch, selection
from apps.jobs.models import Job
from tests.test_review_ui import review_ui as review_fixture
from tests.test_review_ui import save, values

review_ui = review_fixture


def prepared(ui):
    client, file, actor, *_ = ui
    save(ui)
    client.post(reverse("archive_review_detail", args=[file.pk]), values(file, "inspect", explicit="on"))
    file.refresh_from_db()
    return selection(file, actor)


def test_only_individually_inspected_current_reviewer_can_select_and_approve(review_ui):
    client, file, actor, *_ = review_ui
    assert selection(file, actor) == ""
    token = prepared(review_ui)
    assert token and client.get(reverse("archive_review_queue")).context["page"][0].batch_token
    assert not selection(file, get_user_model().objects.create_user("other-batch-reviewer"))
    jobs = approve_batch([token], actor=actor, explicit=True)
    assert len(jobs) == 1 and file.assignments.count() == 0
    file.refresh_from_db()
    assert file.review_state == "APPROVAL_REQUESTED" and not m.ArchiveFile.objects.usable().exists()
    assert m.AuditEvent.objects.filter(event="APPROVAL_REQUESTED", actor=actor).count() == 1


@pytest.mark.parametrize(
    "case", ["unsigned", "duplicate", "unconfirmed", "other-reviewer", "stale", "changed", "unknown"]
)
def test_invalid_batch_never_enqueues_partial_jobs(review_ui, case):
    _client, file, actor, *_ = review_ui
    token = prepared(review_ui)
    tokens, explicit, reviewer = [token], True, actor
    if case == "unsigned":
        tokens = ["forged"]
    elif case == "duplicate":
        tokens = [token, token]
    elif case == "unconfirmed":
        explicit = False
    elif case == "other-reviewer":
        reviewer = get_user_model().objects.create_user("batch-foreign")
    elif case == "stale":
        m.ArchiveFile.objects.filter(pk=file.pk).update(revision=file.revision + 1)
    elif case == "changed":
        m.SourceFile.objects.filter(pk=file.source_version.source_file_id).update(revision=999)
    elif case == "unknown":
        tokens.append("unknown-second-item")
    before = Job.objects.count()
    with pytest.raises(ValidationError):
        approve_batch(tokens, actor=reviewer, explicit=explicit)
    assert Job.objects.count() == before and not m.ArchiveFile.objects.usable().exists()


def test_new_proposal_invalidates_persistent_inspection_and_batch_token(review_ui):
    _client, file, actor, arrangement, _variant, parts, _path = review_ui
    old = prepared(review_ui)
    s.create_proposal(
        file.pk, actor=actor, arrangement_id=arrangement.pk, part_ids=[parts[0].pk], expected_revision=file.revision
    )
    file.refresh_from_db()
    assert not selection(file, actor)
    with pytest.raises(ValidationError):
        approve_batch([old], actor=actor, explicit=True)
    assert m.ReviewInspection.objects.count() == 1


def test_batch_is_post_csrf_and_auth_protected(review_ui):
    _client, file, actor, *_ = review_ui
    token = prepared(review_ui)
    url = reverse("archive_review_batch")
    assert Client().post(url, {"versions": [token], "confirm": "on"}).status_code == 302
    strict = Client(enforce_csrf_checks=True)
    strict.force_login(actor)
    assert strict.get(url).status_code == 405
    assert strict.post(url, {"versions": [token], "confirm": "on"}).status_code == 403
    strict.get(reverse("archive_review_queue"))
    csrf = strict.cookies["notenarchiv_csrftoken"].value
    response = strict.post(url, {"versions": [token], "confirm": "on", "csrfmiddlewaretoken": csrf})
    assert response.status_code == 302 and Job.objects.filter(status="QUEUED").count() == 1


def test_navigation_does_not_record_inspection(review_ui):
    client, file, *_ = review_ui
    second = m.ArchiveFile.objects.create(
        source_version=file.source_version,
        kind="DERIVATIVE",
        root_kind="PROCESSED",
        relative_path="Synthetic/derived.pdf",
        sha256="a" * 64,
        byte_size=1,
        derived_from=file,
        processing_profile="synthetic",
        processing_version="1",
    )
    response = client.get(reverse("archive_review_detail", args=[file.pk]))
    assert response.status_code == 200 and not m.ReviewInspection.objects.exists()
    assert response.context["following"] is None and second.pk != file.pk


def test_second_enqueue_failure_rolls_back_every_batch_request(review_ui, monkeypatch):
    import hashlib

    from apps.archive import publication
    from tests.archive_fixtures import PAGE
    from tests.test_archive_workflow import receipt

    client, file, actor, arrangement, variant, parts, path = review_ui
    first = prepared(review_ui)
    folder = file.source_version.source_file.folder
    data = path.read_bytes()
    version, _ = s.observe_version(
        folder.pk,
        "Synthetic/second.pdf",
        sha256=hashlib.sha256(data).hexdigest(),
        byte_size=len(data),
        pdf_state="VALID",
        page_info=[PAGE],
    )
    second, _ = receipt(s.register_base(version.pk, "_Ungeprueft/second.pdf"))
    (path.parent / "second.pdf").write_bytes(data)
    save((client, second, actor, arrangement, variant, parts, path.parent / "second.pdf"))
    client.post(reverse("archive_review_detail", args=[second.pk]), values(second, "inspect", explicit="on"))
    second.refresh_from_db()
    token = selection(second, actor)
    original, calls = publication._enqueue, []

    def fail_second(*args, **kwargs):
        calls.append(1)
        if len(calls) == 2:
            raise ValidationError("Synthetic second reservation conflict")
        return original(*args, **kwargs)

    monkeypatch.setattr(publication, "_enqueue", fail_second)
    before = Job.objects.count()
    with pytest.raises(ValidationError):
        approve_batch([first, token], actor=actor, explicit=True)
    assert Job.objects.count() == before and not m.ArchiveProposal.objects.filter(state="APPROVAL_REQUESTED").exists()
    assert not m.AuditEvent.objects.filter(event="APPROVAL_REQUESTED").exists()


def test_expired_selection_and_corrupt_clean_copy_are_rejected(review_ui, monkeypatch):
    from django.core import signing

    _client, file, actor, _arrangement, _variant, _parts, path = review_ui
    token = prepared(review_ui)
    with monkeypatch.context() as clock:
        clock.setattr(signing.time, "time", lambda: 0)
        expired = selection(file, actor)
    with pytest.raises(ValidationError):
        approve_batch([expired], actor=actor, explicit=True)
    path.write_bytes(b"Synthetic changed managed bytes")
    with pytest.raises(ValueError):
        approve_batch([token], actor=actor, explicit=True)
    assert not Job.objects.filter(status="QUEUED").exists()


def test_previous_source_version_cannot_be_selected_after_new_hash(review_ui):
    _client, file, actor, *_ = review_ui
    prepared(review_ui)
    source = file.source_version.source_file
    s.observe_version(source.folder_id, source.relative_path, sha256="b" * 64, byte_size=1)
    file = review_services.review_file(file.pk)
    assert not selection(file, actor)
