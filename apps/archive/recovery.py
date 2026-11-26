"""Explicit exact-byte reconstruction of a missing acknowledged CLEAN copy."""

from contextlib import ExitStack, suppress
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F

from apps.archive import models as m
from apps.archive import publication as p
from apps.archive import services as s
from apps.jobs.models import Job
from apps.jobs.services import lifecycle, queue
from core import files

EFFECT = "restore-clean"
PAYLOAD_FIELDS = {"restore_file_id", "publication_operation_id"}


def validate_payload(payload):
    if set(payload) != PAYLOAD_FIELDS or any(not isinstance(payload[key], str) for key in PAYLOAD_FIELDS):
        raise ValueError("Invalid CLEAN restoration payload")
    return {key: str(UUID(payload[key])) for key in sorted(PAYLOAD_FIELDS)}


def _load(file_id, using, *, operation_id=None):
    file = (
        m.ArchiveFile.objects.using(using)
        .select_related("publication_operation__intent", "source_version__source_file")
        .get(pk=file_id)
    )
    if (
        file.kind != "BASE"
        or file.root_kind != "CLEAN"
        or not file.publication_operation_id
        or (operation_id is not None and str(file.publication_operation_id) != operation_id)
    ):
        raise ValidationError("Restoration requires the current acknowledged CLEAN publication.")
    file.full_clean()
    operation = file.publication_operation
    operation.full_clean()
    if operation.state != "APPLIED" or operation.expected_receipt != {
        "root": file.root_kind,
        "path": file.relative_path,
        "sha256": file.sha256,
        "size": file.byte_size,
    }:
        raise ValidationError("Restoration receipt does not identify the current CLEAN copy.")
    return file


def queue_restore(file_id, *, using="default"):
    """Queue an explicitly requested restore of an absent, acknowledged CLEAN path."""
    file = _load(file_id, using)
    payload = {"restore_file_id": str(file.pk), "publication_operation_id": str(file.publication_operation_id)}
    with p._root("CLEAN") as root:
        _require_missing(file, root)
    with transaction.atomic(using=using):
        # Serialize requests on SQLite without changing the confirmed revision or its pins.
        if (
            not m.ArchiveFile.objects.using(using)
            .filter(pk=file.pk, publication_operation_id=file.publication_operation_id, revision=file.revision)
            .update(revision=F("revision"))
        ):
            raise s.ArchiveConflict()
        jobs = Job.objects.using(using).filter(kind=Job.Kind.ARCHIVE_PUBLISH, payload__restore_file_id=str(file.pk))
        if jobs.filter(operations__key=EFFECT, operations__state__in=["PENDING", "REVIEW_REQUIRED"]).exists():
            raise ValidationError("An uncertain CLEAN restoration requires review.")
        existing = jobs.filter(
            payload__publication_operation_id=payload["publication_operation_id"], status__in=["QUEUED", "RUNNING"]
        ).first()
        return existing or queue.enqueue(Job.Kind.ARCHIVE_PUBLISH, payload, using=using)


def _current(context):
    payload = validate_payload(context.payload)
    return _load(payload["restore_file_id"], context.using, operation_id=payload["publication_operation_id"])


def _intent_payload(file):
    return {
        "file_id": str(file.pk),
        "publication_operation_id": str(file.publication_operation_id),
        **file.publication_operation.expected_receipt,
    }


def _stage_path(job_id, attempt):
    return f".staging/{job_id.hex}/attempt-{attempt}.pdf"


def _require_missing(file, root):
    if root.directory_spelling(file.relative_path) != file.relative_path or root.collides(file.relative_path):
        raise ValidationError("The recorded CLEAN destination already exists.")
    original_stage = file.publication_operation.staged_path
    if original_stage and root.exists(original_stage):
        raise ValidationError("Retained original publication proof requires review.")


def _stage_exact(context, file, roots, stage_path):
    clean = roots["CLEAN"]
    processor = p._processor(roots["DATA"], context.checkpoint)

    def stage(source, path):
        return files.stage_copy(
            source,
            path,
            clean,
            stage_path,
            sha256=file.sha256,
            size=file.byte_size,
            processor=processor,
            checkpoint=context.checkpoint,
        )

    historical = (
        file.operations.using(context.using)
        .filter(state="APPLIED", target_root="CLEAN", expected_sha256=file.sha256, expected_size=file.byte_size)
        .exclude(pk=file.publication_operation_id)
        .order_by("-created_at")[:8]
    )
    for operation in historical:
        operation.full_clean()
        if not clean.exists(operation.target_path):
            continue
        try:
            return stage(clean, operation.target_path)
        except files.FileError as error:
            if error.code not in {"SOURCE_CHANGED", "UNSAFE_FILE", "COPY_MISMATCH"}:
                raise
    return stage(roots["RAW"], file.source_version.source_file.relative_path)


def _verify_result(context, file, root, intent, *, require_stage):
    stage_path = _stage_path(context.job_id, intent.attempt)
    retained = stage_path if require_stage or root.exists(stage_path) else None
    files.verify_published(
        root,
        file.relative_path,
        sha256=file.sha256,
        size=file.byte_size,
        staged_path=retained,
        checkpoint=context.checkpoint,
        durable=require_stage,
    )
    return retained


def run(context):
    file = _current(context)
    effect = _intent_payload(file)
    with ExitStack() as stack:
        roots = p._open_roots(stack, context.using)
        clean = roots["CLEAN"]
        applied = (
            Job.objects.using(context.using)
            .get(pk=context.job_id)
            .operations.filter(key=EFFECT, state="APPLIED", payload=effect, result=effect)
            .first()
        )
        if applied is not None:
            retained = _verify_result(context, file, clean, applied, require_stage=False)
            if retained:
                files.release_stage(clean, retained, file.relative_path)
            return
        _require_missing(file, clean)
        context.commit_metadata(lambda: _set_health(file, context.using, "MISSING"))
        staged_path = _stage_path(context.job_id, context.attempt_number)
        staged = _stage_exact(context, file, roots, staged_path)
        try:
            clean.prepare_parent(file.relative_path)

            def apply():
                try:
                    exact_receipt = _intent_payload(_current(context))
                except (ValidationError, m.ArchiveFile.DoesNotExist):
                    raise lifecycle.NoEffect("The acknowledged publication changed.") from None
                if exact_receipt != effect:
                    raise lifecycle.NoEffect("The acknowledged publication changed.")
                try:
                    files.publish(clean, staged, file.relative_path)
                except files.FileError as error:
                    if error.code in {"DESTINATION_EXISTS", "STAGING_CHANGED", "UNSAFE_DESTINATION"}:
                        raise lifecycle.NoEffect("CLEAN restoration did not publish.") from None
                    raise
                return effect

            context.publish(EFFECT, effect, apply)
            files.release_stage(clean, staged_path, file.relative_path)
        finally:
            # A retained two-link inode is proof of an unacknowledged effect.
            # A pre-publication stage is safe to discard only when no intent is unresolved.
            unresolved = (
                Job.objects.using(context.using)
                .get(pk=context.job_id)
                .operations.filter(key=EFFECT)
                .exclude(state="ABANDONED")
                .exists()
            )
            if not unresolved:
                with suppress(files.FileError, OSError):
                    files.discard_stage(clean, staged_path, files.identity(staged.info))


def acknowledge(context, intent):
    file = _current(context)
    effect = _intent_payload(file)
    if intent.key != EFFECT or intent.payload != effect or intent.result != effect:
        raise ValidationError("Restoration receipt does not match the acknowledged CLEAN copy.")
    _set_health(file, context.using, "AVAILABLE")


def _set_health(file, using, state):
    changed = (
        m.ArchiveFile.objects.using(using)
        .filter(
            pk=file.pk,
            revision=file.revision,
            publication_operation_id=file.publication_operation_id,
            publication_state=file.publication_state,
        )
        .update(publication_state=state)
    )
    if changed != 1:
        raise s.ArchiveConflict()


def reconcile(context, intent):
    file = _current(context)
    effect = _intent_payload(file)
    if intent.key != EFFECT or intent.payload != effect:
        return "REVIEW_REQUIRED", {}
    with ExitStack() as stack:
        clean = p._open_roots(stack, context.using)["CLEAN"]
        if not clean.exists(file.relative_path):
            return ("REVIEW_REQUIRED" if clean.collides(file.relative_path) else "ABANDONED"), {}
        try:
            _verify_result(context, file, clean, intent, require_stage=True)
        except (files.FileError, OSError):
            return "REVIEW_REQUIRED", {}
    return "APPLIED", effect


def recover_cleanup(context):
    file = _current(context)
    effect = _intent_payload(file)
    applied = (
        Job.objects.using(context.using)
        .get(pk=context.job_id)
        .operations.filter(key=EFFECT, state="APPLIED", payload=effect, result=effect)
        .first()
    )
    if applied is None:
        return
    with ExitStack() as stack:
        clean = p._open_roots(stack, context.using)["CLEAN"]
        retained = _verify_result(context, file, clean, applied, require_stage=False)
        if retained:
            files.release_stage(clean, retained, file.relative_path)
