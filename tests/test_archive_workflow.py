"""Database workflow evidence only; physical publication is tested by WP-14."""

import uuid
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.archive import models as m
from apps.archive import services as s
from apps.catalog import models as catalog
from apps.catalog.services import save_record
from apps.jobs.models import AttemptRecord, Job, OperationIntent


def revision(file):
    file.refresh_from_db()
    return file.revision


def receipt(file, *, kind="COPY", proposal=None, path=None):
    """Synthetic APPLIED ledger input for metadata tests, not a simulated file copy."""
    now = timezone.now()
    job = Job.objects.create(kind="ARCHIVE_PUBLISH", attempt=1, status="SUCCEEDED", finished_at=now)
    AttemptRecord.objects.create(job=job, number=1, status="SUCCEEDED", started_at=now, finished_at=now)
    operation = s.plan_publication(
        file.pk,
        job_id=job.pk,
        target_path=path or file.relative_path,
        kind=kind,
        proposal_id=proposal.pk if proposal else None,
        expected_revision=revision(file),
    )
    intent = OperationIntent.objects.create(
        job=job,
        key=operation.effect_key,
        attempt=1,
        state="APPLIED",
        payload=operation.effect_payload,
        result=operation.expected_receipt,
    )
    updated = s.apply_publication_receipt(operation.pk, intent_id=intent.pk, expected_revision=revision(file))
    return updated, operation


@pytest.fixture
def reviewed_inputs(archive):
    folder, version, file, data = archive
    file, _ = receipt(file)
    actor = get_user_model().objects.create_user("synthetic-archive-reviewer")
    other = get_user_model().objects.create_user("synthetic-other-reviewer")
    work = save_record(catalog.Work(title="Synthetic archive work"))
    arrangement = save_record(catalog.Arrangement(work=work))
    variant = save_record(catalog.InstrumentVariant(name="Synthetic archive instrument"))
    parts = [save_record(catalog.Part(instrument=variant, code=str(number))) for number in (1, 2, 3)]
    return folder, version, file, actor, other, arrangement, parts


def draft(file, actor, arrangement, parts):
    return s.create_proposal(
        file.pk,
        actor=actor,
        arrangement_id=arrangement.pk if arrangement else None,
        part_ids=[part.pk for part in parts],
        expected_revision=revision(file),
    )


def inspect(file, proposal, actor):
    return s.record_inspection(
        proposal.pk, actor=actor, inspected_sha256=file.sha256, explicit=True, expected_revision=revision(file)
    )


def confirm(file, proposal, actor, *, path="Synthetic work/synthetic-parts.pdf"):
    inspect(file, proposal, actor)
    s.request_approval(proposal.pk, actor=actor, expected_revision=revision(file))
    file, operation = receipt(file, kind="CANONICALIZE", proposal=proposal, path=path)
    return s.complete_approval(proposal.pk, actor=actor, operation_id=operation.pk, expected_revision=revision(file))


def test_combined_pdf_has_multiple_explicit_confirmed_assignments(reviewed_inputs):
    _folder, _version, file, actor, _other, arrangement, parts = reviewed_inputs
    proposal = draft(file, actor, arrangement, parts[:2])
    file = confirm(file, proposal, actor)
    assert file.review_state == "CONFIRMED" and file.arrangement_id == arrangement.pk
    assert set(m.ArchiveAssignment.objects.usable().values_list("part_id", flat=True)) == {
        part.pk for part in parts[:2]
    }
    assert m.ArchiveFile.objects.usable().get().pk == file.pk


def test_derivative_needs_its_own_inspection_and_approval(reviewed_inputs):
    _folder, version, file, actor, _other, arrangement, parts = reviewed_inputs
    file = confirm(file, draft(file, actor, arrangement, parts[:1]), actor)
    derivative = m.ArchiveFile.objects.create(
        source_version=version,
        root_kind="PROCESSED",
        relative_path="_Ungeprueft/derived.pdf",
        sha256="2" * 64,
        byte_size=512,
        kind="DERIVATIVE",
        derived_from=file,
        processing_profile="synthetic",
        processing_version="1",
    )
    derivative, _ = receipt(derivative, kind="DERIVATIVE")
    proposal = draft(derivative, actor, arrangement, parts[:1])
    with pytest.raises(ValidationError):
        s.request_approval(proposal.pk, actor=actor, expected_revision=revision(derivative))
    derivative = confirm(derivative, proposal, actor, path="Synthetic work/derived-parts.pdf")
    assert derivative.review_state == "CONFIRMED" and m.ArchiveFile.objects.usable().count() == 2
    assert derivative.approved_proposal.inspections.get().inspected_sha256 == derivative.sha256
    assert derivative.sha256 != file.sha256


def test_unknown_arrangement_or_missing_inspection_cannot_be_confirmed(reviewed_inputs):
    _folder, _version, file, actor, _other, arrangement, parts = reviewed_inputs
    proposal = draft(file, actor, None, parts[:1])
    inspect(file, proposal, actor)
    with pytest.raises(ValidationError):
        s.request_approval(proposal.pk, actor=actor, expected_revision=revision(file))
    proposal = draft(file, actor, arrangement, parts[:1])
    with pytest.raises(ValidationError):
        s.request_approval(proposal.pk, actor=actor, expected_revision=revision(file))
    assert not m.ArchiveFile.objects.usable().exists()


def test_source_index_recognition_review_and_availability_stay_independent(reviewed_inputs):
    folder, version, file, actor, _other, arrangement, parts = reviewed_inputs
    file = confirm(file, draft(file, actor, arrangement, parts[:1]), actor)
    folder.index_state = "PARTIAL_FAILURE"
    folder.save()
    source = m.SourceFile.objects.get(pk=version.source_file_id)
    s.mark_source_missing(source.pk, expected_revision=source.revision)
    file.candidate_state = "CONFLICT"
    file.save()
    assert m.ArchiveFile.objects.usable().filter(pk=file.pk).exists()
    file.publication_state = "MISSING"
    file.save()
    file.refresh_from_db()
    assert file.review_state == "CONFIRMED" and not m.ArchiveFile.objects.usable().exists()


def test_inspection_belongs_to_reviewer_hash_and_proposal_revision(reviewed_inputs):
    _folder, _version, file, actor, other, arrangement, parts = reviewed_inputs
    proposal = draft(file, actor, arrangement, parts[:1])
    for explicit, digest in [(False, file.sha256), (True, "0" * 64)]:
        with pytest.raises(ValidationError):
            s.record_inspection(
                proposal.pk,
                actor=actor,
                inspected_sha256=digest,
                explicit=explicit,
                expected_revision=revision(file),
            )
    inspect(file, proposal, actor)
    with pytest.raises(ValidationError):
        s.request_approval(proposal.pk, actor=other, expected_revision=revision(file))
    newer = draft(file, actor, arrangement, parts[1:2])
    assert proposal.inspections.count() == 1 and not newer.inspections.exists()
    with pytest.raises(ValidationError):
        s.request_approval(newer.pk, actor=actor, expected_revision=revision(file))
    with pytest.raises(s.ArchiveConflict):
        inspect(file, proposal, actor)


def test_stale_edits_rollback_revision_and_new_snapshot(reviewed_inputs):
    _folder, _version, file, actor, _other, arrangement, parts = reviewed_inputs
    old_revision = revision(file)
    proposal = draft(file, actor, arrangement, parts[:1])
    current = revision(file)
    with pytest.raises(s.ArchiveConflict):
        s.create_proposal(file.pk, actor=actor, arrangement_id=None, part_ids=[], expected_revision=old_revision)
    assert revision(file) == current and file.current_proposal_id == proposal.pk
    assert file.proposals.count() == 1


def test_reanalysis_and_rejected_correction_keep_previous_approved_assignments(reviewed_inputs):
    _folder, _version, file, actor, _other, arrangement, parts = reviewed_inputs
    first = draft(file, actor, arrangement, parts[:2])
    file = confirm(file, first, actor)
    newer = draft(file, actor, arrangement, parts[2:])
    assert m.ArchiveFile.objects.usable().get().approved_proposal_id == first.pk
    assert m.ArchiveAssignment.objects.usable().count() == 2
    s.reject_proposal(newer.pk, actor=actor, expected_revision=revision(file))
    assert m.ArchiveFile.objects.usable().get().approved_proposal_id == first.pk
    newer = draft(file, actor, arrangement, parts[1:])
    file = confirm(file, newer, actor, path="Synthetic work/corrected-parts.pdf")
    assert set(m.ArchiveAssignment.objects.usable().values_list("part_id", flat=True)) == {
        part.pk for part in parts[1:]
    }
    assert file.assignments.get(part=parts[0]).state == "WITHDRAWN"
    first.refresh_from_db()
    assert first.state == "APPROVED" and first.inspections.count() == 1
    assert file.operations.filter(state="APPLIED").count() == 3


def test_withdrawal_retains_bytes_assignments_and_review_history(reviewed_inputs):
    _folder, _version, file, actor, _other, arrangement, parts = reviewed_inputs
    file = confirm(file, draft(file, actor, arrangement, parts[:1]), actor)
    original = file.sha256, file.relative_path, file.approved_proposal_id
    pending = draft(file, actor, arrangement, parts[1:2])
    inspect(file, pending, actor)
    s.request_approval(pending.pk, actor=actor, expected_revision=revision(file))
    file = s.withdraw(file.pk, actor=actor, expected_revision=revision(file))
    pending.refresh_from_db()
    assert pending.state == "REJECTED" and file.review_state == "WITHDRAWN"
    assert (file.sha256, file.relative_path, file.approved_proposal_id) == original
    assert file.assignments.count() == 1 and not m.ArchiveAssignment.objects.usable().exists()
    assert m.AuditEvent.objects.filter(archive_file=file, event="WITHDRAWN", actor=actor).exists()


@pytest.mark.parametrize("field", ["state", "key", "payload", "result", "attempt", "job"])
def test_mismatched_or_pending_receipt_cannot_publish(archive, field):
    _folder, _version, file, _data = archive
    now = timezone.now()
    job = Job.objects.create(kind="ARCHIVE_PUBLISH", attempt=1, status="SUCCEEDED", finished_at=now)
    AttemptRecord.objects.create(job=job, number=1, status="SUCCEEDED", started_at=now, finished_at=now)
    operation = s.plan_publication(
        file.pk, job_id=job.pk, target_path=file.relative_path, expected_revision=revision(file)
    )
    values = dict(
        job=job,
        key=operation.effect_key,
        payload=operation.effect_payload,
        result=operation.expected_receipt,
        attempt=1,
        state="APPLIED",
    )
    values[field] = {
        "state": "PENDING",
        "key": "another-effect",
        "payload": {},
        "result": {},
        "attempt": 2,
        "job": Job.objects.create(kind="ARCHIVE_PUBLISH"),
    }[field]
    intent = OperationIntent.objects.create(**values)
    before = revision(file)
    with pytest.raises(ValidationError):
        s.apply_publication_receipt(operation.pk, intent_id=intent.pk, expected_revision=before)
    assert revision(file) == before and file.publication_state == "UNPUBLISHED"
    operation.refresh_from_db()
    assert operation.state == "PLANNED" and operation.intent_id is None


def test_failed_or_other_publication_does_not_confirm(reviewed_inputs):
    _folder, _version, file, actor, _other, arrangement, parts = reviewed_inputs
    proposal = draft(file, actor, arrangement, parts[:1])
    inspect(file, proposal, actor)
    s.request_approval(proposal.pk, actor=actor, expected_revision=revision(file))
    operation = s.plan_publication(
        file.pk,
        job_id=Job.objects.create(kind="ARCHIVE_PUBLISH").pk,
        kind="CANONICALIZE",
        proposal_id=proposal.pk,
        target_path="Synthetic/failed.pdf",
        expected_revision=revision(file),
    )
    operation.state = "FAILED"
    operation.save()
    with pytest.raises(ValidationError):
        s.complete_approval(proposal.pk, actor=actor, operation_id=operation.pk, expected_revision=revision(file))
    assert not m.ArchiveFile.objects.usable().exists()
    assert not file.assignments.exists()
    assert revision(file) and file.review_state == "APPROVAL_REQUESTED"


def test_inactive_references_block_new_approval_and_pending_request_blocks_edits(reviewed_inputs):
    _folder, _version, file, actor, _other, arrangement, parts = reviewed_inputs
    proposal = draft(file, actor, arrangement, parts[:1])
    inspect(file, proposal, actor)
    parts[0].active = False
    save_record(parts[0], expected_revision=parts[0].revision)
    with pytest.raises(ValidationError):
        s.request_approval(proposal.pk, actor=actor, expected_revision=revision(file))
    parts[0].active = True
    save_record(parts[0], expected_revision=parts[0].revision)
    s.request_approval(proposal.pk, actor=actor, expected_revision=revision(file))
    with pytest.raises(ValidationError):
        draft(file, actor, arrangement, parts[1:2])


def test_stage_requires_exact_running_attempt_and_verified_hash(archive):
    _folder, _version, file, _data = archive
    job = Job.objects.create(
        kind="ARCHIVE_PUBLISH",
        status="RUNNING",
        attempt=2,
        lease_owner=uuid.uuid4(),
        lease_expires_at=timezone.now() + timedelta(minutes=1),
    )
    AttemptRecord.objects.create(job=job, number=2, started_at=timezone.now(), status="RUNNING")
    operation = s.plan_publication(
        file.pk, job_id=job.pk, target_path=file.relative_path, expected_revision=revision(file)
    )
    for attempt, path, digest in [
        (1, ".staging/old.pdf", file.sha256),
        (2, "escape.pdf", file.sha256),
        (2, ".staging/bad.pdf", "0" * 64),
    ]:
        with pytest.raises(ValidationError):
            s.record_stage(
                operation.pk, attempt=attempt, staged_path=path, verified_sha256=digest, verified_size=file.byte_size
            )
    operation = s.record_stage(
        operation.pk,
        attempt=2,
        staged_path=".staging/current.pdf",
        verified_sha256=file.sha256,
        verified_size=file.byte_size,
    )
    assert operation.state == "STAGED" and operation.attempt_record.number == 2
