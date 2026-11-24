"""Real archive worker effects, bounded staging and exact receipt reconciliation."""

import os
from contextlib import ExitStack, suppress
from pathlib import Path, PurePosixPath
from uuid import UUID, uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import connections, transaction
from django.db.models import F

from apps.archive import models as m
from apps.archive import services as s
from apps.catalog.models import Work
from apps.jobs.models import Job
from apps.jobs.services import lifecycle, queue
from core import files
from core.naming import component, part_filename, pdf_name, with_suffix
from core.paths import storage_key
from core.pdf import Limits, Processor


def validate_payload(payload):
    if set(payload) != {"operation_id"} or not isinstance(payload["operation_id"], str):
        raise ValueError("Invalid archive operation payload")
    return {"operation_id": str(UUID(payload["operation_id"]))}


def _root(kind, *, writable=False):
    if kind not in m.RootKind.values:
        raise ValidationError("Unsupported managed archive root.")
    return files.Root(settings.CURATED_DIR if kind == "CLEAN" else settings.PROCESSED_DIR, writable=writable)


def _reserved(kind, path, using, *, exclude=None):
    key = storage_key(path)
    return (
        m.ArchiveFile.objects.using(using).filter(root_kind=kind, path_key=key).exclude(pk=exclude).exists()
        or m.FileOperation.objects.using(using).filter(target_root=kind, target_key=key).exists()
    )


def choose_target(kind, preferred, identifier, *, exclude=None, using="default"):
    """Read-only planning outside a write transaction; reservation is rechecked inside."""
    parts = list(PurePosixPath(preferred).parts)
    for index in range(len(parts) - 1):
        prefix = storage_key(str(PurePosixPath(*parts[: index + 1]))) + "/"
        known = (
            m.ArchiveFile.objects.using(using)
            .filter(root_kind=kind, path_key__startswith=prefix)
            .values_list("relative_path", flat=True)
            .first()
            or m.FileOperation.objects.using(using)
            .filter(target_root=kind, target_key__startswith=prefix)
            .values_list("target_path", flat=True)
            .first()
        )
        if known:
            parts[: index + 1] = PurePosixPath(known).parts[: index + 1]
    with _root(kind) as root:
        preferred = root.directory_spelling(str(PurePosixPath(*parts)))
        candidates = [preferred] + [with_suffix(preferred, identifier.hex, number) for number in range(100)]
        for candidate in candidates:
            if not _reserved(kind, candidate, using, exclude=exclude) and not root.collides(candidate):
                return candidate
    raise ValidationError("No safe collision-free archive destination is available.")


def _enqueue(file, path, *, proposal=None, using):
    if _reserved(file.root_kind, path, using, exclude=file.pk):
        raise s.ArchiveConflict()
    operation_id = uuid4()
    job = queue.enqueue(Job.Kind.ARCHIVE_PUBLISH, {"operation_id": str(operation_id)}, using=using)
    s.plan_publication(
        file.pk,
        job_id=job.pk,
        target_path=path,
        kind="CANONICALIZE" if proposal else "COPY",
        proposal_id=proposal.pk if proposal else None,
        operation_id=operation_id,
        expected_revision=file.revision,
        using=using,
    )
    return job


def queue_copy(version_id, *, using="default"):
    version = m.SourceVersion.objects.using(using).select_related("source_file").get(pk=version_id)
    previous = m.ArchiveFile.objects.using(using).filter(source_version=version, kind="BASE").first()
    if previous:
        active = previous.operations.using(using).filter(job__status__in=["QUEUED", "RUNNING"]).first()
        if active:
            return previous, active.job
        if previous.publication_state == "AVAILABLE":
            return previous, previous.publication_operation.job
    preferred = f"_Ungeprueft/{version.source_file_id.hex}/{pdf_name(version.source_file.relative_path)}"
    path = choose_target("CLEAN", preferred, version.pk, exclude=previous.pk if previous else None, using=using)
    with transaction.atomic(using=using):
        if not m.SourceVersion.objects.using(using).filter(pk=version_id).update(revision=F("revision") + 1):
            raise ValidationError("Source version does not exist.")
        file = m.ArchiveFile.objects.using(using).filter(source_version=version, kind="BASE").first()
        if file:
            active = file.operations.using(using).filter(job__status__in=["QUEUED", "RUNNING"]).first()
            if active:
                return file, active.job
            if file.publication_state == "AVAILABLE":
                return file, file.publication_operation.job
        else:
            file = s.register_base(version_id, path, using=using)
        job = _enqueue(file, path, using=using)
        file.refresh_from_db(using=using)
        return file, job


def canonical_path(proposal, *, using="default"):
    arrangement = proposal.arrangement
    if arrangement is None:
        raise ValidationError("A controlled arrangement is required.")
    work = arrangement.work
    title = component(work.title)
    if Work.objects.using(using).filter(title_key=work.title_key).exclude(pk=work.pk).exists():
        title += "--" + work.pk.hex[:12]
    edition = component(
        " - ".join(value for value in (arrangement.arranger, arrangement.edition) if value) or "Original"
    )
    groups = {}
    for entry in (
        proposal.parts.using(using)
        .select_related("part__instrument")
        .order_by(
            "part__instrument__name_key",
            "part__instrument__family_key",
            "part__instrument__transposition_key",
            "part__instrument_id",
            "part__code_key",
        )
    ):
        part = entry.part
        variant = part.instrument
        family = f" [{variant.family}]" if variant.family else ""
        label = f"{variant.transposition} {variant.get_clef_display()} {variant.name}{family}"
        groups.setdefault(variant.pk, (label, []))[1].append(part.code)
    if not groups:
        raise ValidationError("Canonical publication requires at least one controlled part.")
    filename = part_filename(list(groups.values()), proposal.archive_file.source_version_id.hex)
    return str(PurePosixPath(title, edition, filename))


def queue_canonical(proposal_id, *, actor, expected_revision, using="default"):
    proposal = (
        m.ArchiveProposal.objects.using(using).select_related("archive_file", "arrangement__work").get(pk=proposal_id)
    )
    file = proposal.archive_file
    path = choose_target(
        file.root_kind, canonical_path(proposal, using=using), file.source_version_id, exclude=file.pk, using=using
    )
    with transaction.atomic(using=using):
        # request_approval resolves a proposal before its own write-first block.
        # When nested here, that read would establish a SQLite reader snapshot
        # which cannot safely upgrade while the worker holds a writer lock.
        # Acquire the short writer boundary first without incrementing twice.
        if (
            not m.ArchiveFile.objects.using(using)
            .filter(pk=file.pk, revision=expected_revision)
            .update(revision=F("revision"))
        ):
            raise s.ArchiveConflict()
        proposal = s.request_approval(proposal_id, actor=actor, expected_revision=expected_revision, using=using)
        file = m.ArchiveFile.objects.using(using).get(pk=file.pk)
        existing = proposal.operations.using(using).filter(job__status__in=["QUEUED", "RUNNING"]).first()
        return existing.job if existing else _enqueue(file, path, proposal=proposal, using=using)


def _operation(context):
    operation = (
        m.FileOperation.objects.using(context.using)
        .select_related("archive_file__source_version__source_file", "proposal", "job")
        .get(pk=context.payload["operation_id"])
    )
    if operation.job_id != context.job_id or operation.kind not in {"COPY", "CANONICALIZE"}:
        raise ValidationError("Operation does not belong to this supported archive job.")
    return operation


def _processor(data_root, checkpoint):
    with data_root.parent(".staging/pdf/placeholder", create=True):
        pass
    return Processor(
        data_root.path / ".staging" / "pdf",
        checkpoint=checkpoint,
        limits=Limits(
            max_bytes=min(settings.PDF_MAX_BYTES, 104_857_600),
            max_pixels=min(settings.PDF_MAX_RENDER_PIXELS, 30_000_000),
            memory_bytes=268_435_456,
        ),
    )


def _open_roots(stack, using):
    paths = [
        Path(settings.SOURCE_DIR),
        Path(settings.CURATED_DIR),
        Path(settings.PROCESSED_DIR),
        Path(connections[using].settings_dict["NAME"]).parent,
    ]
    if any(
        first.is_relative_to(second) or second.is_relative_to(first)
        for index, first in enumerate(paths)
        for second in paths[:index]
    ):
        raise files.FileError("OVERLAPPING_ROOTS")
    roots = [stack.enter_context(files.Root(path, writable=index > 0)) for index, path in enumerate(paths)]
    if len({files.identity(os.fstat(root.fd)) for root in roots}) != len(roots):
        raise files.FileError("OVERLAPPING_ROOTS")
    return {"RAW": roots[0], "CLEAN": roots[1], "PROCESSED": roots[2], "DATA": roots[3]}


def _check_request(operation, using):
    file = m.ArchiveFile.objects.using(using).get(pk=operation.archive_file_id)
    proposal = s._current_proposal(file, operation.proposal_id, using)
    if proposal.state != "APPROVAL_REQUESTED":
        raise ValidationError("Publication requires the current approval request.")
    actor = s._actor(proposal.requested_by_id, using)
    s._eligible_proposal(file, proposal, actor, using)
    return actor


def acknowledge(context, intent):
    """Pure DB hook: atomically acknowledge a normal or recovered exact effect."""
    operation = _operation(context)
    using = context.using
    if (
        intent.key != operation.effect_key
        or intent.payload != operation.effect_payload
        or intent.result != operation.expected_receipt
    ):
        raise ValidationError("Receipt does not identify this physical publication.")
    if operation.state == "APPLIED":
        if operation.intent_id != intent.pk:
            raise ValidationError("Applied operation has another durable receipt.")
        return
    if operation.kind == "CANONICALIZE":
        try:
            with transaction.atomic(using=using):
                actor = _check_request(operation, using)
                file = m.ArchiveFile.objects.using(using).get(pk=operation.archive_file_id)
                file = s.apply_publication_receipt(
                    operation.pk, intent_id=intent.pk, expected_revision=file.revision, using=using
                )
                s.complete_approval(
                    operation.proposal_id,
                    actor=actor,
                    operation_id=operation.pk,
                    expected_revision=file.revision,
                    using=using,
                )
            return
        except ValidationError:
            # A reviewer may withdraw/change eligibility while the predecessor is
            # dead. Retain the real effect as history, without selecting its path
            # or restoring approval. Never undo/delete the published file.
            s.record_applied_operation(operation.pk, intent_id=intent.pk, using=using)
            file = m.ArchiveFile.objects.using(using).get(pk=operation.archive_file_id)
            proposal = m.ArchiveProposal.objects.using(using).get(pk=operation.proposal_id)
            if proposal.state == "APPROVAL_REQUESTED":
                proposal.state = "REJECTED"
                proposal.save(using=using)
                if file.current_proposal_id == proposal.pk and file.review_state == "APPROVAL_REQUESTED":
                    file.review_state = "REJECTED"
                    file.revision += 1
                    file.save(using=using)
                s._audit(
                    file,
                    m.AuditEvent.Event.REJECTED,
                    using,
                    after={"proposal": str(proposal.pk), "reason": "PUBLICATION_CONFLICT"},
                )
            return
    file = m.ArchiveFile.objects.using(using).get(pk=operation.archive_file_id)
    s.apply_publication_receipt(operation.pk, intent_id=intent.pk, expected_revision=file.revision, using=using)


def _prune_old_stages(context, operation, root):
    for number in range(1, context.attempt_number):
        if (
            not operation.job.history.using(context.using)
            .filter(number=number, status__in=["FAILED", "CANCELLED"])
            .exists()
        ):
            raise lifecycle.ReviewRequired()
        path = f".staging/{operation.pk.hex}/attempt-{number}.pdf"
        if root.exists(path):
            info = root.metadata(path)
            if info.st_uid != os.geteuid():
                raise files.FileError("UNSAFE_STAGING")
            context.checkpoint()
            files.discard_stage(root, path, files.identity(info))


def _run(context):
    operation = _operation(context)
    file = operation.archive_file
    with ExitStack() as stack:
        roots = _open_roots(stack, context.using)
        target = roots[operation.target_root]
        processor = _processor(roots["DATA"], context.checkpoint)
        if operation.state == "APPLIED":
            stage_path = (
                operation.staged_path if operation.staged_path and target.exists(operation.staged_path) else None
            )
            files.verify_published(
                target,
                operation.target_path,
                sha256=operation.expected_sha256,
                size=operation.expected_size,
                staged_path=stage_path,
                checkpoint=context.checkpoint,
            )
        else:
            if operation.kind == "CANONICALIZE":
                _check_request(operation, context.using)
                source, source_path = target, file.relative_path
                previous = file.publication_operation
                if previous and previous.staged_path and source.exists(previous.staged_path):
                    files.release_stage(source, previous.staged_path, source_path)
            else:
                source, source_path = roots["RAW"], file.source_version.source_file.relative_path
            _prune_old_stages(context, operation, target)
            context.checkpoint(10)
            staged_path = f".staging/{operation.pk.hex}/attempt-{context.attempt_number}.pdf"
            stage = files.stage_copy(
                source,
                source_path,
                target,
                staged_path,
                sha256=operation.expected_sha256,
                size=operation.expected_size,
                processor=processor,
                checkpoint=context.checkpoint,
            )
            try:
                context.commit_metadata(
                    lambda: s.record_stage(
                        operation.pk,
                        attempt=context.attempt_number,
                        staged_path=stage.path,
                        verified_sha256=stage.sha256,
                        verified_size=stage.size,
                        using=context.using,
                    )
                )
                context.checkpoint(80)
                with target.parent(operation.target_path, create=True):
                    pass

                def apply():
                    if operation.kind == "CANONICALIZE":
                        try:
                            _check_request(operation, context.using)
                        except ValidationError:
                            raise lifecycle.NoEffect("Approval request changed before publication") from None
                    try:
                        files.publish(target, stage, operation.target_path)
                    except files.FileError as error:
                        if error.code in {"DESTINATION_EXISTS", "STAGING_CHANGED", "UNSAFE_DESTINATION"}:
                            raise lifecycle.NoEffect("Archive publication did not occur") from None
                        raise
                    return operation.expected_receipt

                context.publish(operation.effect_key, operation.effect_payload, apply)
                operation.refresh_from_db(using=context.using)
            finally:
                # Cancellation before publication removes only our unlinked
                # temporary inode. A linked uncertain effect retains its proof.
                with suppress(files.FileError, OSError):
                    files.discard_stage(target, stage.path, files.identity(stage.info))
        context.checkpoint()
        if operation.staged_path:
            files.release_stage(target, operation.staged_path, operation.target_path)
        if operation.kind == "CANONICALIZE" and (
            operation.proposal.state != "APPROVED"
            or not m.ArchiveFile.objects.using(context.using)
            .filter(pk=file.pk, approved_proposal_id=operation.proposal_id, review_state="CONFIRMED")
            .exists()
        ):
            raise lifecycle.ReviewRequired()


def run(context):
    try:
        _run(context)
    except (ValueError, ValidationError, OSError):

        def record_failure():
            uncertain = (
                Job.objects.using(context.using)
                .get(pk=context.job_id)
                .operations.filter(state__in=["PENDING", "REVIEW_REQUIRED"])
                .exists()
            )
            m.FileOperation.objects.using(context.using).filter(
                pk=context.payload["operation_id"],
                job_id=context.job_id,
                state__in=["PLANNED", "STAGED", "FAILED", "ABANDONED"],
            ).update(state="REVIEW_REQUIRED" if uncertain else "FAILED")

        context.commit_metadata(record_failure)
        raise


def reconcile(context, intent):
    operation = _operation(context)
    if (
        intent.key != operation.effect_key
        or intent.payload != operation.effect_payload
        or operation.attempt != intent.attempt
        or not operation.staged_path
    ):
        return "REVIEW_REQUIRED", {}
    with ExitStack() as stack:
        roots = _open_roots(stack, context.using)
        target = roots[operation.target_root]
        if not target.exists(operation.target_path):
            return "ABANDONED", {}
        try:
            processor = _processor(roots["DATA"], context.checkpoint)
            files.verify_published(
                target,
                operation.target_path,
                sha256=operation.expected_sha256,
                size=operation.expected_size,
                staged_path=operation.staged_path,
                processor=processor,
                checkpoint=context.checkpoint,
                durable=True,
            )
        except (files.FileError, OSError, ValueError):
            return "REVIEW_REQUIRED", {}
        return "APPLIED", operation.expected_receipt


def register():
    queue.HANDLERS[Job.Kind.ARCHIVE_PUBLISH] = queue.Handler(
        validate_payload, run, idempotent=True, max_attempts=3, reconcile=reconcile, acknowledge=acknowledge
    )


def verified_bytes(file_id, *, using="default", checkpoint=lambda: None):
    """Bounded verified managed bytes, including pending review copies.

    Callers own authentication and selection policy. This is not approval or a
    public download route, and never accepts a client-supplied filesystem path.
    """
    file = m.ArchiveFile.objects.using(using).select_related("publication_operation__intent").get(pk=file_id)
    if file.publication_state != "AVAILABLE" or not file.publication_operation_id:
        raise files.FileError("FILE_UNAVAILABLE")
    file.full_clean()
    operation = file.publication_operation
    if operation.state != "APPLIED" or operation.intent.state != "APPLIED":
        raise files.FileError("FILE_UNAVAILABLE")
    if not 0 < file.byte_size <= min(settings.PDF_MAX_BYTES, 104_857_600):
        raise files.FileError("LIMIT_EXCEEDED")
    with _root(file.root_kind) as root:
        stage_path = operation.staged_path if operation.staged_path and root.exists(operation.staged_path) else None
        data, _info = files.verify_published(
            root,
            file.relative_path,
            sha256=file.sha256,
            size=file.byte_size,
            staged_path=stage_path,
            checkpoint=checkpoint,
        )
        return data
