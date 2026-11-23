"""Immutable authorization, exact pin retention and atomic job creation."""

import pytest
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models.deletion import ProtectedError

from apps.archive import models as archive
from apps.archive.services import withdraw
from apps.exports.models import GenerationRun, GenerationSnapshot, SnapshotInput
from apps.exports.snapshot_services import authorize, load_pinned_inputs
from apps.jobs.models import Job
from apps.jobs.services import queue
from apps.projects import models as m
from apps.projects.preflight_services import build_report, report_token
from tests.test_resolution import resolver_inputs as _resolution_fixture

resolver_inputs = _resolution_fixture


def permission(inputs, *, missing=False):
    actor, project, arr, parts, people, positions, first, *_ = inputs
    if not missing:
        for position in positions[:2]:
            m.PartOverride.objects.create(
                project=project,
                participant=people[2],
                position=position,
                desired_part=parts[1],
                edition=first.assignments.get(),
            )
    person = people[0] if missing else people[2]
    report = build_report(project.pk, participant_ids=[person.pk])
    return dict(
        project_id=project.pk,
        participant_ids=[person.pk],
        position_ids=list(report.session.positions),
        token=report_token(report, actor),
        acknowledgements=sorted(report.missing_keys),
        actor=actor,
    )


def test_authorization_atomically_pins_and_enqueues(resolver_inputs):
    values = permission(resolver_inputs)
    run = authorize(**values)
    assert run.job.kind == "GENERATE" and run.job.status == "QUEUED"
    assert run.snapshot.inputs.count() == 2
    assert len(run.snapshot.payload["positions"]) == 3
    snapshot, pins = load_pinned_inputs(run.snapshot.pk)
    assert snapshot.sha256 == run.job.payload["sha256"] and len(pins) == 2
    assert snapshot.actor_id == values["actor"].pk
    assert authorize(**values).pk == run.pk
    assert GenerationRun.objects.count() == 1
    with pytest.raises(queue.InvalidPayload, match="bound job"):
        queue.enqueue("GENERATE", run.job.payload)


def test_missing_ack_is_snapshot_bound_no_silent_skip(resolver_inputs):
    values = permission(resolver_inputs, missing=True)
    with pytest.raises(ValidationError):
        authorize(**{**values, "acknowledgements": []})
    assert not Job.objects.filter(kind="GENERATE").exists()
    run = authorize(**values)
    assert run.snapshot.acknowledgements == values["acknowledgements"]
    assert run.snapshot.inputs.count() == 0
    assert [cell["status"] for cell in run.snapshot.payload["cells"]] == ["MISSING", "MISSING", "RESERVE"]


def test_stale_token_and_full_subset_rejected(resolver_inputs):
    values = permission(resolver_inputs)
    with pytest.raises(ValidationError):
        authorize(**{**values, "token": "forged"})
    m.Project.objects.filter(pk=values["project_id"]).update(revision=2)
    with pytest.raises(ValidationError):
        authorize(**values)
    assert not GenerationSnapshot.objects.exists()


def test_snapshot_remains_unchanged_after_project_edits(resolver_inputs):
    values = permission(resolver_inputs)
    run = authorize(**values)
    actor, project, arr, parts, people, positions, first, *_ = resolver_inputs
    original = run.snapshot.payload
    m.ProjectParticipant.objects.filter(pk=people[2].pk).update(default_part=parts[0], display_name="Changed synthetic")
    m.ProjectPosition.objects.filter(pk=positions[0].pk).update(arrangement=None)
    run.snapshot.refresh_from_db()
    snapshot, pins = load_pinned_inputs(run.snapshot.pk)
    assert snapshot.payload == original and len(pins) == 2
    with pytest.raises(ValidationError, match="immutable"):
        snapshot.save()
    with pytest.raises(ValidationError, match="immutable"):
        GenerationSnapshot.objects.filter(pk=snapshot.pk).update(payload={})
    with pytest.raises(ValidationError):
        snapshot.inputs.all().delete()


def test_pinned_file_withdrawal_and_deletion_denied(resolver_inputs):
    values = permission(resolver_inputs)
    run = authorize(**values)
    first = resolver_inputs[6]
    first.refresh_from_db()
    with pytest.raises(ValidationError, match="Pinned"):
        withdraw(first.pk, actor=values["actor"], expected_revision=first.revision)
    with pytest.raises(ProtectedError), transaction.atomic():
        archive.ArchiveAssignment.objects.filter(archive_file=first).delete()
    assert run.snapshot.inputs.count() == 2


def test_unexpected_file_change_fails_closed(resolver_inputs, settings):
    values = permission(resolver_inputs)
    run = authorize(**values)
    first = resolver_inputs[6]
    (settings.CURATED_DIR / first.relative_path).write_bytes(b"corrupted synthetic pin")
    with pytest.raises(ValidationError, match="verification"):
        load_pinned_inputs(run.snapshot.pk)


def test_enqueue_failure_rolls_back_snapshot_pins_and_run(resolver_inputs, monkeypatch):
    values = permission(resolver_inputs)

    def fail(*args, **kwargs):
        raise queue.InvalidPayload("synthetic enqueue failure")

    monkeypatch.setattr(queue, "enqueue", fail)
    with pytest.raises(queue.InvalidPayload):
        authorize(**values)
    assert not GenerationSnapshot.objects.exists() and not SnapshotInput.objects.exists()
    assert not GenerationRun.objects.exists()


def test_job_payload_cannot_bypass_snapshot_authorization(resolver_inputs):
    with pytest.raises(queue.InvalidPayload):
        queue.enqueue("GENERATE", {"snapshot_id": "00000000-0000-0000-0000-000000000000", "sha256": "0" * 64})
    assert not Job.objects.filter(kind="GENERATE").exists()


def test_database_guards_prevent_pinned_identity_mutation(resolver_inputs):
    from django.db import IntegrityError, connection

    values = permission(resolver_inputs)
    run = authorize(**values)
    first = resolver_inputs[6]
    with pytest.raises(IntegrityError), transaction.atomic():
        archive.ArchiveFile.objects.filter(pk=first.pk).update(review_state="WITHDRAWN")
    with pytest.raises(IntegrityError), transaction.atomic(), connection.cursor() as cursor:
        cursor.execute("UPDATE exports_generationsnapshot SET sha256=%s WHERE id=%s", ["0" * 64, run.snapshot.pk.hex])


def test_edit_between_verification_and_enqueue_rejected(resolver_inputs, monkeypatch):
    values = permission(resolver_inputs)
    from apps.exports import snapshot_services as services

    original = services.build_report

    def changed(*args, **kwargs):
        report = original(*args, **kwargs)
        m.ProjectParticipant.objects.filter(pk=values["participant_ids"][0]).update(display_name="Changed synthetic")
        return report

    monkeypatch.setattr(services, "build_report", changed)
    with pytest.raises(ValidationError, match="geändert"):
        authorize(**values)
    assert not GenerationSnapshot.objects.exists() and not GenerationRun.objects.exists()


def test_authorize_endpoint_requires_csrf_and_verified_report(resolver_inputs, client):
    from django.test import Client
    from django.urls import reverse

    values = permission(resolver_inputs)
    client.force_login(values["actor"])
    url = reverse("project_preflight", args=[values["project_id"]])
    payload = {
        "participants": [str(value) for value in values["participant_ids"]],
        "positions": [str(value) for value in values["position_ids"]],
        "token": values["token"],
        "acknowledgements": values["acknowledgements"],
        "action": "authorize",
    }
    csrf = Client(enforce_csrf_checks=True)
    csrf.force_login(values["actor"])
    assert csrf.post(url, payload).status_code == 403
    assert client.post(url, {**payload, "token": "forged"}).status_code == 409
    response = client.post(url, payload)
    assert response.status_code == 200 and response.context["authorized_run"].job.status == "QUEUED"


def test_worker_without_renderer_fails_never_succeeds(resolver_inputs, tmp_path):
    from apps.jobs.services.worker import run_worker

    run = authorize(**permission(resolver_inputs))
    run_worker(tmp_path / "worker.lock", once=True)
    run.job.refresh_from_db()
    assert run.job.status == "FAILED" and run.job.error_code == "HANDLER_FAILED"
    assert run.job.history.count() == 1
    assert GenerationSnapshot.objects.count() == 1


def test_queued_cancel_preserves_authorization(resolver_inputs):
    from apps.jobs.services.lifecycle import request_cancel

    run = authorize(**permission(resolver_inputs, missing=True))
    request_cancel(run.job_id)
    run.job.refresh_from_db()
    assert run.job.status == "CANCELLED"
    assert run.snapshot.positions.count() == 3


def test_full_folder_rejects_personal_position_subset(resolver_inputs):
    values = permission(resolver_inputs)
    report = build_report(
        values["project_id"], participant_ids=values["participant_ids"], position_ids=values["position_ids"][:1]
    )
    with pytest.raises(ValidationError, match="alle gemeinsamen"):
        authorize(
            **{**values, "position_ids": values["position_ids"][:1], "token": report_token(report, values["actor"])}
        )
    assert not GenerationRun.objects.exists()


def test_missing_library_change_at_atomic_recheck_rejected(resolver_inputs, monkeypatch):
    values = permission(resolver_inputs, missing=True)
    from apps.exports import snapshot_services as service

    original = service.build_report

    def change(*args, **kwargs):
        report = original(*args, **kwargs)
        archive.ArchiveFile.objects.filter(pk=resolver_inputs[6].pk).update(publication_state="CORRUPT")
        return report

    monkeypatch.setattr(service, "build_report", change)
    with pytest.raises(ValidationError, match="geändert"):
        authorize(**values)
    assert not GenerationRun.objects.exists()
