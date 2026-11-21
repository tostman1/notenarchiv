"""Version-bound explicit review, compatible controlled parts and durable enqueue."""

from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from apps.archive import models as m
from apps.catalog import models as c
from apps.jobs.models import Job
from tests.test_archive_workflow import receipt


@pytest.fixture
def review_ui(archive, settings, tmp_path, client, monkeypatch):
    _folder, _version, file, data = archive
    file, _ = receipt(file)
    settings.CURATED_DIR = tmp_path / "clean"
    path = settings.CURATED_DIR / file.relative_path
    path.parent.mkdir(parents=True)
    path.write_bytes(data)
    # Metadata-only enqueue fixture: actual no-clobber planning/worker publication
    # remains mandatory in Linux end-to-end tests, not this cross-platform test.
    monkeypatch.setattr(
        "apps.archive.publication.choose_target",
        lambda kind, path, *args, **kwargs: path.removesuffix(".pdf") + "--" + uuid4().hex + ".pdf",
    )
    actor = get_user_model().objects.create_user("synthetic-review")
    client.force_login(actor)
    work = c.Work.objects.create(title="Synthetic review work")
    arrangement = c.Arrangement.objects.create(work=work)
    variant = c.InstrumentVariant.objects.create(name="Synthetic instrument", transposition="Bb", clef="BASS")
    parts = [c.Part.objects.create(instrument=variant, code=str(n)) for n in (2, 3)]
    return client, file, actor, arrangement, variant, parts, path


def values(file, action, **extra):
    file.refresh_from_db()
    return {
        "action": action,
        "expected_revision": file.revision,
        "source_version": str(file.source_version_id),
        "sha256": file.sha256,
        "proposal": str(file.current_proposal_id) if file.current_proposal_id else "",
        **extra,
    }


def save(ui):
    client, file, _actor, arrangement, variant, parts, _path = ui
    return client.post(
        reverse("archive_review_detail", args=[file.pk]),
        values(
            file,
            "save",
            arrangement=str(arrangement.pk),
            instruments=[str(variant.pk)],
            parts=[str(p.pk) for p in parts],
        ),
    )


def test_get_and_preview_never_count_as_inspection(review_ui):
    client, file, _actor, _arrangement, _variant, _parts, _path = review_ui
    response = client.get(reverse("archive_review_detail", args=[file.pk]))
    assert response.status_code == 200 and "no-store" in response["Cache-Control"]
    assert "PDF-Inhalt" in response.content.decode() and "frame-ancestors 'none'" in response["Content-Security-Policy"]
    assert client.get(reverse("archive_preview:viewer", args=[file.pk])).status_code == 200
    assert not m.ArchiveProposal.objects.exists() and not m.ReviewInspection.objects.exists()
    assert not m.ArchiveFile.objects.usable().exists()


def test_combined_corrected_assignment_inspection_and_approval_are_separate_durable_steps(review_ui):
    client, file, actor, arrangement, _variant, parts, path = review_ui
    before = path.read_bytes()
    assert save(review_ui).status_code == 302
    file.refresh_from_db()
    proposal = file.current_proposal
    assert proposal.arrangement_id == arrangement.pk and proposal.parts.count() == 2
    url = reverse("archive_review_detail", args=[file.pk])
    assert client.post(url, values(file, "approve", explicit="on")).status_code == 409
    assert client.post(url, values(file, "inspect")).status_code == 400
    assert client.post(url, values(file, "inspect", explicit="on")).status_code == 302
    assert proposal.inspections.get().reviewer_id == actor.pk
    assert client.get(url).context["inspected"]
    response = client.post(url, values(file, "approve", explicit="on"))
    assert response.status_code == 302 and "/jobs/" in response.url
    file.refresh_from_db()
    assert file.review_state == "APPROVAL_REQUESTED" and not file.assignments.exists()
    assert not m.ArchiveFile.objects.usable().exists()
    job = Job.objects.get(status="QUEUED")
    assert job.file_operations.get().proposal_id == proposal.pk
    assert set(proposal.parts.values_list("part_id", flat=True)) == {p.pk for p in parts}
    assert path.read_bytes() == before and m.AuditEvent.objects.filter(event="INSPECTED", actor=actor).count() == 1


@pytest.mark.parametrize(
    "field,value",
    [("expected_revision", 999), ("source_version", str(uuid4())), ("sha256", "f" * 64), ("proposal", str(uuid4()))],
)
def test_stale_or_other_version_cannot_be_inspected(review_ui, field, value):
    client, file, *_ = review_ui
    save(review_ui)
    data = values(file, "inspect", explicit="on")
    data[field] = value
    assert client.post(reverse("archive_review_detail", args=[file.pk]), data).status_code == 409
    assert not m.ReviewInspection.objects.exists()


def test_rejection_and_new_correction_require_new_inspection_and_other_reviewer_cannot_approve(review_ui):
    client, file, _actor, *_ = review_ui
    save(review_ui)
    url = reverse("archive_review_detail", args=[file.pk])
    assert client.post(url, values(file, "inspect", explicit="on")).status_code == 302
    old = file.current_proposal_id
    assert client.post(url, values(file, "reject", explicit="on")).status_code == 302
    assert m.ArchiveProposal.objects.get(pk=old).state == "REJECTED"
    assert client.get(reverse("archive_preview:viewer", args=[file.pk])).status_code == 404
    assert save(review_ui).status_code == 302
    file.refresh_from_db()
    assert file.review_state == "PENDING" and file.current_proposal_id != old
    assert not client.get(url).context["inspected"]
    client.post(url, values(file, "inspect", explicit="on"))
    other = get_user_model().objects.create_user("synthetic-other-review-ui")
    client.force_login(other)
    assert client.post(url, values(file, "approve", explicit="on")).status_code == 409


def test_incompatible_inactive_and_empty_choices_are_rejected(review_ui):
    client, file, _actor, arrangement, variant, parts, _path = review_ui
    other = c.InstrumentVariant.objects.create(name="Different instrument", clef="TREBLE")
    data = values(file, "save", arrangement=str(arrangement.pk), instruments=[str(other.pk)], parts=[str(parts[0].pk)])
    assert client.post(reverse("archive_review_detail", args=[file.pk]), data).status_code == 400
    c.Part.objects.filter(pk=parts[0].pk).update(active=False)
    data["instruments"] = [str(variant.pk)]
    assert client.post(reverse("archive_review_detail", args=[file.pk]), data).status_code == 400
    assert not m.ArchiveProposal.objects.exists()


def test_modified_copy_blocks_inspection_and_failed_publication_does_not_confirm(review_ui):
    client, file, _actor, _arrangement, _variant, _parts, path = review_ui
    save(review_ui)
    url = reverse("archive_review_detail", args=[file.pk])
    original = path.read_bytes()
    path.write_bytes(b"Synthetic corrupted copy")
    assert client.post(url, values(file, "inspect", explicit="on")).status_code == 409
    assert not m.ReviewInspection.objects.exists()
    path.write_bytes(original)
    client.post(url, values(file, "inspect", explicit="on"))
    client.post(url, values(file, "approve", explicit="on"))
    Job.objects.filter(status="QUEUED").update(status="FAILED", error_code="HANDLER_FAILED")
    assert not m.ArchiveFile.objects.usable().exists()
    assert "fehlgeschlagen" in client.get(url).content.decode().lower()
    response = client.post(url, values(file, "approve", explicit="on"))
    assert response.status_code == 302 and Job.objects.filter(status="QUEUED").count() == 1
    assert not m.ArchiveFile.objects.usable().exists()


def test_review_actions_require_auth_csrf_and_no_arbitrary_file_id(review_ui):
    _client, file, actor, *_ = review_ui
    url = reverse("archive_review_detail", args=[file.pk])
    anonymous = Client()
    assert anonymous.get(url).status_code == 302 and anonymous.post(url, values(file, "save")).status_code == 302
    strict = Client(enforce_csrf_checks=True)
    strict.force_login(actor)
    assert strict.post(url, values(file, "save")).status_code == 403
    assert strict.get(reverse("archive_review_detail", args=[uuid4()])).status_code == 404
    assert strict.get(url).status_code == 200
