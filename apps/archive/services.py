"""Short write-first SQLite transactions over protected archive metadata.

No filesystem I/O or automatic approval. Callers own stable source observations,
publication evidence, authentication and actual visual presentation.
"""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.archive import models as m
from apps.archive.source_pages import record_source_pages
from apps.catalog.models import Arrangement, Part
from apps.jobs.models import AttemptRecord, OperationIntent


class ArchiveConflict(ValidationError):
    def __init__(self):
        super().__init__("Archive metadata changed; refresh and retry.")


def _actor(actor, using):
    identifier = actor.pk if hasattr(actor, "pk") else actor
    try:
        return get_user_model().objects.using(using).get(pk=identifier, is_active=True)
    except (get_user_model().DoesNotExist, ValueError, TypeError):
        raise ValidationError("An active reviewer is required.") from None


def _lock_file(identifier, expected_revision, using):
    if type(expected_revision) is not int or expected_revision < 1:
        raise ArchiveConflict()
    if (
        not m.ArchiveFile.objects.using(using)
        .filter(pk=identifier, revision=expected_revision)
        .update(revision=F("revision") + 1)
    ):
        raise ArchiveConflict()
    return m.ArchiveFile.objects.using(using).get(pk=identifier)


def _audit(target, event, using, *, actor=None, before=None, after=None):
    fields = {
        m.SourceFolder: "folder",
        m.SourceFile: "source_file",
        m.SourceVersion: "source_version",
        m.ArchiveFile: "archive_file",
        m.FileOperation: "file_operation",
    }
    return m.AuditEvent.objects.using(using).create(
        event=event, actor=actor, before=before or {}, after=after or {}, **{fields[type(target)]: target}
    )


def observe_version(
    folder_id,
    relative_path,
    *,
    sha256,
    byte_size,
    mtime_ns=None,
    pdf_state=m.SourceVersion.PdfState.UNCHECKED,
    page_info=None,
    using="default",
):
    """Content identity is per source file/hash, never global hash deduplication."""
    with transaction.atomic(using=using):
        if not m.SourceFolder.objects.using(using).filter(pk=folder_id).update(revision=F("revision") + 1):
            raise ValidationError("Source folder does not exist.")
        folder = m.SourceFolder.objects.using(using).get(pk=folder_id)
        source, created = m.SourceFile.objects.using(using).get_or_create(
            relative_path=relative_path, defaults={"folder": folder}
        )
        if source.folder_id != folder.pk:
            raise ValidationError("Source file belongs to another folder.")
        version, new_version = m.SourceVersion.objects.using(using).get_or_create(
            source_file=source,
            sha256=sha256,
            defaults={
                "byte_size": byte_size,
                "source_mtime_ns": mtime_ns,
                "pdf_state": pdf_state,
                "page_info": [] if page_info is None else page_info,
            },
        )
        if version.byte_size != byte_size:
            raise ValidationError("Known source hash has inconsistent byte size.")
        if new_version and version.pdf_state == m.SourceVersion.PdfState.VALID:
            record_source_pages(m.SourcePage, version, using=using)
        changed = source.current_version_id is not None and source.current_version_id != version.pk
        reappeared = source.presence == m.SourceFile.Presence.MISSING
        source.current_version = version
        source.observed_size, source.observed_mtime_ns = byte_size, mtime_ns
        source.presence = m.SourceFile.Presence.CHANGED if changed else m.SourceFile.Presence.PRESENT
        source.last_seen_at = timezone.now()
        source.revision += 1
        source.save(using=using)
        if created or new_version or reappeared:
            _audit(
                version,
                m.AuditEvent.Event.SOURCE_OBSERVED,
                using,
                after={"source": str(source.pk), "sha256": sha256, "changed": changed},
            )
        return version, new_version


def mark_source_missing(identifier, *, expected_revision, using="default"):
    with transaction.atomic(using=using):
        if (
            not m.SourceFile.objects.using(using)
            .filter(pk=identifier, revision=expected_revision)
            .update(revision=F("revision") + 1)
        ):
            raise ArchiveConflict()
        source = m.SourceFile.objects.using(using).get(pk=identifier)
        previous = source.presence
        source.presence = m.SourceFile.Presence.MISSING
        source.save(using=using)
        if previous != source.presence:
            _audit(source, m.AuditEvent.Event.SOURCE_MISSING, using, before={"presence": previous})
        return source


def record_validation(
    identifier, *, expected_revision, pdf_state, page_info, original_crop_boxes=None, using="default"
):
    with transaction.atomic(using=using):
        if (
            not m.SourceVersion.objects.using(using)
            .filter(pk=identifier, revision=expected_revision)
            .update(revision=F("revision") + 1)
        ):
            raise ArchiveConflict()
        version = m.SourceVersion.objects.using(using).get(pk=identifier)
        if version.pdf_state != m.SourceVersion.PdfState.UNCHECKED and (
            version.pdf_state != pdf_state or version.page_info != page_info
        ):
            raise ValidationError("Recorded PDF validation cannot be silently replaced.")
        previous = version.pdf_state
        version.pdf_state, version.page_info = pdf_state, page_info
        version.save(using=using)
        if pdf_state == m.SourceVersion.PdfState.VALID:
            record_source_pages(m.SourcePage, version, using=using, original_crop_boxes=original_crop_boxes)
        if previous != pdf_state:
            _audit(
                version,
                m.AuditEvent.Event.VALIDATED,
                using,
                before={"pdf_state": previous},
                after={"pdf_state": pdf_state},
            )
        return version


def register_base(version_id, relative_path, *, using="default"):
    """Register an unavailable copy identity; this never claims a filesystem effect."""
    with transaction.atomic(using=using):
        if not m.SourceVersion.objects.using(using).filter(pk=version_id).update(revision=F("revision") + 1):
            raise ValidationError("Source version does not exist.")
        version = m.SourceVersion.objects.using(using).get(pk=version_id)
        previous = m.ArchiveFile.objects.using(using).filter(source_version=version, kind="BASE").first()
        if previous:
            if previous.relative_path != relative_path:
                raise ValidationError("Use the existing file identity and an explicit publication/move operation.")
            return previous
        return m.ArchiveFile.objects.using(using).create(
            source_version=version, relative_path=relative_path, sha256=version.sha256, byte_size=version.byte_size
        )


def _proposal_references(arrangement_id, part_ids, using):
    if (
        arrangement_id is not None
        and not Arrangement.objects.using(using).filter(pk=arrangement_id, active=True, work__active=True).exists()
    ):
        raise ValidationError("Choose an active arrangement.")
    if not isinstance(part_ids, (list, tuple)) or len(part_ids) > 1000 or len(set(map(str, part_ids))) != len(part_ids):
        raise ValidationError("Choose at most 1000 distinct controlled parts.")
    parts = list(Part.objects.using(using).filter(pk__in=part_ids, active=True, instrument__active=True))
    if len(parts) != len(part_ids):
        raise ValidationError("Choose active controlled parts and notation variants.")
    return parts


def create_proposal(file_id, *, actor, arrangement_id, part_ids, expected_revision, using="default"):
    with transaction.atomic(using=using):
        file = _lock_file(file_id, expected_revision, using)
        actor = _actor(actor, using)
        if file.current_proposal_id and file.current_proposal.state == "APPROVAL_REQUESTED":
            raise ValidationError("An approval/publication request is already pending.")
        parts = _proposal_references(arrangement_id, part_ids, using)
        proposal = m.ArchiveProposal.objects.using(using).create(
            archive_file=file,
            revision=file.revision,
            arrangement_id=arrangement_id,
            created_by=actor,
        )
        for part in parts:
            m.ProposalPart.objects.using(using).create(proposal=proposal, part=part)
        proposal.sealed = True
        proposal.save(using=using)
        file.current_proposal = proposal
        if file.review_state == "REJECTED" and file.approved_proposal_id is None:
            file.review_state = "PENDING"
        file.save(using=using)
        _audit(
            file,
            m.AuditEvent.Event.PROPOSAL_CREATED,
            using,
            actor=actor,
            after={"proposal": str(proposal.pk), "revision": proposal.revision, "part_count": len(parts)},
        )
        return proposal


def _proposal_file_id(identifier, using):
    result = (
        m.ArchiveProposal.objects.using(using).filter(pk=identifier).values_list("archive_file_id", flat=True).first()
    )
    if result is None:
        raise ValidationError("Proposal does not exist.")
    return result


def _current_proposal(file, identifier, using):
    if str(file.current_proposal_id) != str(identifier):
        raise ArchiveConflict()
    proposal = m.ArchiveProposal.objects.using(using).get(pk=identifier)
    if not proposal.sealed:
        raise ValidationError("Proposal construction is incomplete.")
    return proposal


def _available(file):
    if file.publication_state != "AVAILABLE" or file.source_version.pdf_state != "VALID":
        raise ValidationError("Visual review requires an available validated copy.")
    file.full_clean()
    if file.publication_operation.intent.state != "APPLIED":
        raise ValidationError("Publication is not durably acknowledged.")


def record_inspection(proposal_id, *, actor, inspected_sha256, explicit, expected_revision, using="default"):
    file_id = _proposal_file_id(proposal_id, using)  # Read before starting the write transaction.
    if explicit is not True:
        raise ValidationError("An explicit visual-review attestation is required.")
    with transaction.atomic(using=using):
        file = _lock_file(file_id, expected_revision, using)
        actor = _actor(actor, using)
        proposal = _current_proposal(file, proposal_id, using)
        _available(file)
        if inspected_sha256 != file.sha256 or proposal.state != "DRAFT":
            raise ValidationError("Inspection must identify the current draft and exact version.")
        inspection, created = m.ReviewInspection.objects.using(using).get_or_create(
            proposal=proposal,
            reviewer=actor,
            defaults={"inspected_sha256": inspected_sha256, "explicit_attestation": True},
        )
        if created:
            _audit(
                file,
                m.AuditEvent.Event.INSPECTED,
                using,
                actor=actor,
                after={"proposal": str(proposal.pk), "inspection": str(inspection.pk), "sha256": file.sha256},
            )
        return inspection


def _eligible_proposal(file, proposal, actor, using):
    _available(file)
    parts = list(proposal.parts.using(using).values_list("part_id", flat=True))
    if proposal.arrangement_id is None or not parts:
        raise ValidationError("Approval requires an arrangement and at least one part.")
    _proposal_references(proposal.arrangement_id, parts, using)
    if (
        not proposal.inspections.using(using)
        .filter(reviewer=actor, inspected_sha256=file.sha256, explicit_attestation=True)
        .exists()
    ):
        raise ValidationError("This reviewer must inspect this exact version/proposal first.")
    return parts


def request_approval(proposal_id, *, actor, expected_revision, using="default"):
    file_id = _proposal_file_id(proposal_id, using)
    with transaction.atomic(using=using):
        file = _lock_file(file_id, expected_revision, using)
        actor = _actor(actor, using)
        proposal = _current_proposal(file, proposal_id, using)
        _eligible_proposal(file, proposal, actor, using)
        if proposal.state == "APPROVAL_REQUESTED" and proposal.requested_by_id == actor.pk:
            return proposal
        if proposal.state != "DRAFT":
            raise ValidationError("Proposal is not eligible for a new approval request.")
        proposal.state, proposal.requested_by = "APPROVAL_REQUESTED", actor
        proposal.save(using=using)
        if file.review_state != "CONFIRMED":
            file.review_state = "APPROVAL_REQUESTED"
            file.save(using=using)
        _audit(
            file,
            m.AuditEvent.Event.APPROVAL_REQUESTED,
            using,
            actor=actor,
            after={"proposal": str(proposal.pk), "sha256": file.sha256},
        )
        return proposal


def plan_publication(
    file_id,
    *,
    job_id,
    target_path,
    kind="COPY",
    proposal_id=None,
    operation_id=None,
    expected_revision,
    using="default",
):
    """Reserve metadata only. WP-14 performs streaming, validation and no-clobber publication."""
    with transaction.atomic(using=using):
        file = _lock_file(file_id, expected_revision, using)
        if kind == "CANONICALIZE":
            if proposal_id is None:
                raise ValidationError("Canonical publication requires an explicit proposal.")
            proposal = _current_proposal(file, proposal_id, using)
            if proposal.state != "APPROVAL_REQUESTED":
                raise ValidationError("Canonical publication requires an explicit approval request.")
        operation = m.FileOperation.objects.using(using).create(
            **({"id": operation_id} if operation_id is not None else {}),
            archive_file=file,
            job_id=job_id,
            kind=kind,
            proposal_id=proposal_id,
            target_root=file.root_kind,
            target_path=target_path,
            expected_sha256=file.sha256,
            expected_size=file.byte_size,
        )
        _audit(
            operation,
            m.AuditEvent.Event.COPY_PLANNED,
            using,
            after={"file": str(file.pk), "kind": kind, "sha256": file.sha256},
        )
        return operation


def record_stage(operation_id, *, attempt, staged_path, verified_sha256, verified_size, using="default"):
    """Record a worker-verified stage; callers must hold the job's metadata fence."""
    with transaction.atomic(using=using):
        if type(attempt) is not int or attempt < 1:
            raise ValidationError("A running attempt is required.")
        if (
            not m.FileOperation.objects.using(using)
            .filter(pk=operation_id, attempt__lte=attempt, state__in=["PLANNED", "STAGED", "FAILED", "ABANDONED"])
            .update(attempt=attempt)
        ):
            raise ArchiveConflict()
        operation = m.FileOperation.objects.using(using).get(pk=operation_id)
        if operation.job.status != "RUNNING" or operation.job.attempt != attempt:
            raise ValidationError("A current running attempt is required.")
        if operation.expected_sha256 != verified_sha256 or operation.expected_size != verified_size:
            raise ValidationError("Staged bytes do not match the publication intent.")
        operation.staged_path, operation.state = staged_path, "STAGED"
        operation.attempt_record = (
            AttemptRecord.objects.using(using).filter(job_id=operation.job_id, number=attempt).first()
        )
        operation.save(using=using)
        return operation


def record_applied_operation(operation_id, *, intent_id, using="default"):
    """Record a verified physical effect without necessarily selecting its path."""
    with transaction.atomic(using=using):
        if not m.FileOperation.objects.using(using).filter(pk=operation_id).update(attempt=F("attempt")):
            raise ValidationError("Publication operation does not exist.")
        operation = m.FileOperation.objects.using(using).get(pk=operation_id)
        intent = OperationIntent.objects.using(using).filter(pk=intent_id).first()
        if intent is None:
            raise ValidationError("Publication receipt does not exist.")
        previous = operation.state
        operation.intent, operation.state = intent, "APPLIED"
        operation.attempt = intent.attempt
        operation.attempt_record = (
            AttemptRecord.objects.using(using).filter(job_id=operation.job_id, number=intent.attempt).first()
        )
        operation.save(using=using)
        if previous != "APPLIED":
            _audit(
                operation,
                m.AuditEvent.Event.COPY_APPLIED,
                using,
                after={
                    "file": str(operation.archive_file_id),
                    "sha256": operation.expected_sha256,
                    "intent": str(intent_id),
                },
            )
        return operation


def apply_publication_receipt(operation_id, *, intent_id, expected_revision, using="default"):
    """Acknowledge an APPLIED worker receipt, inside its short metadata fence.

    This function does not validate files or perform a filesystem operation.
    Durable verified effects are supplied by WP-14, never by a request boolean.
    """
    file_id = (
        m.FileOperation.objects.using(using).filter(pk=operation_id).values_list("archive_file_id", flat=True).first()
    )
    if file_id is None:
        raise ValidationError("Publication operation does not exist.")
    with transaction.atomic(using=using):
        file = _lock_file(file_id, expected_revision, using)
        operation = record_applied_operation(operation_id, intent_id=intent_id, using=using)
        file.relative_path, file.publication_state = operation.target_path, "AVAILABLE"
        file.publication_operation = operation
        file.save(using=using)
        return file


def complete_approval(proposal_id, *, actor, operation_id, expected_revision, using="default"):
    file_id = _proposal_file_id(proposal_id, using)
    with transaction.atomic(using=using):
        file = _lock_file(file_id, expected_revision, using)
        actor = _actor(actor, using)
        proposal = _current_proposal(file, proposal_id, using)
        parts = _eligible_proposal(file, proposal, actor, using)
        if proposal.state != "APPROVAL_REQUESTED" or proposal.requested_by_id != actor.pk:
            raise ValidationError("Approval request does not belong to this reviewer.")
        operation = m.FileOperation.objects.using(using).get(pk=operation_id)
        if (
            operation.archive_file_id != file.pk
            or operation.proposal_id != proposal.pk
            or operation.kind != "CANONICALIZE"
            or operation.state != "APPLIED"
            or file.publication_operation_id != operation.pk
        ):
            raise ValidationError("Approval requires this proposal's completed canonical publication.")
        previous = {"proposal": str(file.approved_proposal_id), "review_state": file.review_state}
        proposal.state, proposal.approved_by, proposal.approved_at = "APPROVED", actor, timezone.now()
        proposal.save(using=using)
        file.assignments.using(using).exclude(part_id__in=parts).update(state="WITHDRAWN")
        for part_id in parts:
            assignment, _ = m.ArchiveAssignment.objects.using(using).get_or_create(
                archive_file=file,
                part_id=part_id,
                defaults={"accepted_proposal": proposal},
            )
            assignment.accepted_proposal, assignment.state = proposal, "CONFIRMED"
            assignment.save(using=using)
        file.arrangement_id, file.approved_proposal = proposal.arrangement_id, proposal
        file.confirmed_by, file.confirmed_at = actor, proposal.approved_at
        file.review_state = "CONFIRMED"
        file.save(using=using)
        _audit(
            file,
            m.AuditEvent.Event.CONFIRMED,
            using,
            actor=actor,
            before=previous,
            after={"proposal": str(proposal.pk), "operation": str(operation.pk), "part_count": len(parts)},
        )
        return file


def reject_proposal(proposal_id, *, actor, expected_revision, using="default"):
    file_id = _proposal_file_id(proposal_id, using)
    with transaction.atomic(using=using):
        file = _lock_file(file_id, expected_revision, using)
        actor = _actor(actor, using)
        proposal = _current_proposal(file, proposal_id, using)
        if (
            proposal.state not in {"DRAFT", "APPROVAL_REQUESTED"}
            or proposal.operations.using(using).exclude(state__in=["FAILED", "ABANDONED"]).exists()
        ):
            raise ValidationError("Settle any publication operation before rejecting this proposal.")
        proposal.state = "REJECTED"
        proposal.save(using=using)
        if file.approved_proposal_id is None:
            file.review_state = "REJECTED"
            file.save(using=using)
        _audit(file, m.AuditEvent.Event.REJECTED, using, actor=actor, after={"proposal": str(proposal.pk)})
        return proposal


def withdraw(file_id, *, actor, expected_revision, using="default"):
    with transaction.atomic(using=using):
        from apps.exports.models import SnapshotInput

        if SnapshotInput.objects.using(using).filter(archive_file_id=file_id).exists():
            raise ValidationError("Pinned generation inputs cannot be withdrawn; historical authorization is retained.")
        file = _lock_file(file_id, expected_revision, using)
        actor = _actor(actor, using)
        if file.review_state != "CONFIRMED":
            raise ValidationError("Only a confirmed archive file can be withdrawn.")
        if file.current_proposal_id != file.approved_proposal_id and file.current_proposal_id:
            proposal = file.current_proposal
            if proposal.state == "APPROVAL_REQUESTED":
                proposal.state = "REJECTED"
                proposal.save(using=using)
        file.review_state = "WITHDRAWN"
        file.save(using=using)
        _audit(
            file,
            m.AuditEvent.Event.WITHDRAWN,
            using,
            actor=actor,
            after={"sha256": file.sha256, "proposal": str(file.approved_proposal_id)},
        )
        return file
