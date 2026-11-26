"""Durable bounded indexing; only worker-owned effects, never automatic approval."""

import hashlib
import json
from contextlib import ExitStack
from dataclasses import asdict
from pathlib import PurePosixPath
from uuid import UUID

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.archive import models as m
from apps.archive import publication as p
from apps.archive import recognition
from apps.archive import services as s
from apps.jobs.models import Job
from apps.jobs.services import lifecycle, queue
from core import files, inventory
from core.paths import relative_path
from core.pdf import PdfError


def validate_payload(payload):
    if set(payload) != {"scan_id"} or not isinstance(payload["scan_id"], str):
        raise ValueError("Invalid index payload")
    return {"scan_id": str(UUID(payload["scan_id"]))}


def queue_index(selected_path="", *, using="default"):
    """Backend API. WP-16 adds authenticated selection UI; no client roots."""
    path = relative_path(selected_path, allow_root=True)
    with transaction.atomic(using=using):
        # Write first serializes overlapping selection checks on SQLite.
        m.SourceFolder.objects.using(using).get_or_create(relative_path="")
        m.SourceFolder.objects.using(using).filter(relative_path="").update(revision=F("revision") + 1)
        for scan in m.IndexScan.objects.using(using).filter(job__status__in=["QUEUED", "RUNNING", "REVIEW_REQUIRED"]):
            other = scan.selected_path
            if path == other:
                return scan.job
            if not path or not other or path.startswith(other + "/") or other.startswith(path + "/"):
                raise s.ArchiveConflict()
        identifier = m.IndexScan().pk
        job = queue.enqueue(Job.Kind.INDEX_SCAN, {"scan_id": str(identifier)}, using=using)
        m.IndexScan.objects.using(using).create(id=identifier, job=job, selected_path=path)
        return job


class CopyContext:
    """Keep the INDEX_SCAN fence, but select one existing WP-14 operation."""

    def __init__(self, context, operation):
        self.context = context
        self.payload = {"operation_id": str(operation.pk)}

    def __getattr__(self, name):
        return getattr(self.context, name)

    def checkpoint(self, progress=None):
        # WP-14 reports per-copy percentages; INDEX_SCAN owns monotonic global
        # progress. Preserve lease/cancellation checks without regressing it.
        self.context.checkpoint()


def _scan(context):
    return m.IndexScan.objects.using(context.using).get(pk=context.payload["scan_id"], job_id=context.job_id)


def _record_inventory(scan, observed, using):
    directories = {item["path"] for item in observed if item["kind"] == "DIRECTORY"}
    # Include known disappeared subfolders only after a complete traversal.
    for folder in m.SourceFolder.objects.using(using).all():
        if (
            not scan.selected_path
            or folder.relative_path == scan.selected_path
            or folder.relative_path.startswith(scan.selected_path + "/")
        ):
            directories.add(folder.relative_path)
    folders = {}
    for path in sorted(directories):
        folder, _ = m.SourceFolder.objects.using(using).get_or_create(relative_path=path)
        folders[path] = folder
        m.IndexFolder.objects.using(using).create(scan=scan, folder=folder)
        m.SourceFolder.objects.using(using).filter(pk=folder.pk).update(index_state="INDEXING")
    for item in observed:
        if item["kind"] == "DIRECTORY":
            continue
        parent = str(PurePosixPath(item["path"]).parent)
        m.IndexEntry.objects.using(using).create(
            scan=scan,
            folder=folders["" if parent == "." else parent],
            relative_path=item["path"],
            fingerprint=item["fingerprint"],
            kind=item["kind"],
        )
    scan.inventory_ready = True
    scan.save(using=using)


def _failure(context, entry, code):
    context.commit_metadata(
        lambda: m.IndexEntry.objects.using(context.using).filter(pk=entry.pk).update(state="FAILED", error_code=code)
    )


def _verify_existing_copy(context, entry, existing, root):
    try:
        p.verify_receipt_bytes(existing, root, checkpoint=context.checkpoint)
    except files.FileError as error:
        if error.code == "COPY_MISMATCH" or (
            error.code == "LIMIT_EXCEEDED" and root.metadata(existing.relative_path).st_size != existing.byte_size
        ):
            state = "CORRUPT"
        elif error.code == "FILE_IO" and not root.exists(existing.relative_path):
            state = "MISSING"
        else:
            raise
    else:
        state = "AVAILABLE"

    def record_health():
        # This is storage health, so the logical revision pinned by historical
        # exports must survive an outage and exact-byte restoration.
        if state != existing.publication_state and not m.ArchiveFile.objects.using(context.using).filter(
            pk=existing.pk, revision=existing.revision, publication_state=existing.publication_state
        ).update(publication_state=state):
            raise s.ArchiveConflict()
        if state != "AVAILABLE":
            m.IndexEntry.objects.using(context.using).filter(pk=entry.pk).update(
                state="FAILED", error_code="CLEAN_" + state
            )

    if state != "AVAILABLE" or state != existing.publication_state:
        context.commit_metadata(record_health)
    return state == "AVAILABLE"


def _entry(context, entry, roots, processor):
    using = context.using
    version = None
    if entry.kind == "UNSAFE":
        _failure(context, entry, "UNSAFE_FILE")
        return
    if PurePosixPath(entry.relative_path).suffix.casefold() != ".pdf":
        context.commit_metadata(lambda: m.IndexEntry.objects.using(using).filter(pk=entry.pk).update(state="SKIPPED"))
        return
    try:
        digest, data, info = inventory.read_hash(
            roots["RAW"],
            entry.relative_path,
            maximum=min(settings.PDF_MAX_BYTES, 104_857_600),
            expected=entry.fingerprint,
            checkpoint=context.checkpoint,
        )
        version, _ = context.commit_metadata(
            lambda: s.observe_version(
                entry.folder_id,
                entry.relative_path,
                sha256=digest,
                byte_size=info.st_size,
                mtime_ns=info.st_mtime_ns,
                using=using,
            )
        )
        context.commit_metadata(
            lambda: m.IndexEntry.objects.using(using).filter(pk=entry.pk).update(source_version=version, sha256=digest)
        )
        existing = m.ArchiveFile.objects.using(using).filter(source_version=version, kind="BASE").first()
        if existing and existing.publication_operation_id:
            if not _verify_existing_copy(context, entry, existing, roots["CLEAN"]):
                return
            if entry.operation_id:
                p.run(CopyContext(context, entry.operation))
        else:
            inspection = processor.inspect(data, include_text=True)
            if version.pdf_state == "UNCHECKED":
                version = context.commit_metadata(
                    lambda: s.record_validation(
                        version.pk,
                        expected_revision=version.revision,
                        pdf_state="VALID",
                        page_info=[asdict(page) for page in inspection.pages],
                        using=using,
                    )
                )
            if version.pdf_state != "VALID":
                raise files.FileError("INVALID_PDF")
            if not entry.operation_id:
                preferred = f"_Ungeprueft/{version.source_file_id.hex}/{p.pdf_name(entry.relative_path)}"
                path = p.choose_target(
                    "CLEAN", preferred, version.pk, exclude=existing.pk if existing else None, using=using
                )

                def plan():
                    file = existing or s.register_base(version.pk, path, using=using)
                    operation = s.plan_publication(
                        file.pk, job_id=context.job_id, target_path=path, expected_revision=file.revision, using=using
                    )
                    m.IndexEntry.objects.using(using).filter(pk=entry.pk).update(operation=operation)
                    return operation

                operation = context.commit_metadata(plan)
            else:
                operation = entry.operation
            context.commit_metadata(
                lambda: recognition.record_candidate(
                    version.pk,
                    filename=entry.relative_path,
                    text_lines="\n".join(inspection.text or ()).splitlines(),
                    using=using,
                )
            )
            p.run(CopyContext(context, operation))
        context.commit_metadata(lambda: m.IndexEntry.objects.using(using).filter(pk=entry.pk).update(state="COPIED"))
    except PdfError as error:
        pdf_code = error.code
        if (
            version is not None
            and version.pdf_state == "UNCHECKED"
            and error.code in {"INVALID_PDF", "ENCRYPTED_PDF", "LIMIT_EXCEEDED", "UNSUPPORTED_ANNOTATION"}
        ):
            context.commit_metadata(
                lambda: s.record_validation(
                    version.pk,
                    expected_revision=version.revision,
                    pdf_state="LIMIT_EXCEEDED" if pdf_code == "LIMIT_EXCEEDED" else "INVALID",
                    page_info=[],
                    using=using,
                )
            )
        _failure(context, entry, error.code)
    except (files.FileError, OSError, ValidationError) as error:
        if (
            Job.objects.using(using)
            .get(pk=context.job_id)
            .operations.filter(state__in=["PENDING", "REVIEW_REQUIRED"])
            .exists()
        ):
            raise lifecycle.ReviewRequired() from None
        _failure(context, entry, error.code if isinstance(error, files.FileError) else "INDEX_FILE_FAILED")


def _summarize(context, scan):
    using = context.using
    for record in scan.folders.using(using).select_related("folder"):
        entries = list(scan.entries.using(using).filter(folder=record.folder))
        paths = {entry.relative_path for entry in entries}
        for source in record.folder.files.using(using).exclude(relative_path__in=paths):
            s.mark_source_missing(source.pk, expected_revision=source.revision, using=using)
        relevant = [entry for entry in entries if entry.state != "SKIPPED"]
        failed = sum(entry.state == "FAILED" for entry in relevant)
        indexed = sum(entry.state == "COPIED" for entry in relevant)
        fingerprint = hashlib.sha256(
            json.dumps([(e.relative_path, e.sha256, e.state) for e in entries], sort_keys=True).encode()
        ).hexdigest()
        folder = record.folder
        folder.index_state = "PARTIAL_FAILURE" if failed else "INDEXED"
        folder.file_count, folder.failed_count, folder.indexed_count = len(relevant), failed, indexed
        folder.inventory_fingerprint = fingerprint
        folder.save(using=using)
        states = {}
        for file in m.ArchiveFile.objects.using(using).filter(source_version__current_sources__folder=folder):
            for value in (file.review_state, file.candidate_state):
                states[value] = states.get(value, 0) + 1
        record.snapshot = {
            "folder_id": str(folder.pk),
            "scan_id": str(scan.pk),
            "path": folder.relative_path,
            "index_state": folder.index_state,
            "files": len(relevant),
            "indexed": indexed,
            "failed": failed,
            "missing": folder.files.filter(presence="MISSING").count(),
            "states": states,
            "fingerprint": fingerprint,
            "timestamp": timezone.now().isoformat(),
        }
        record.snapshot["duplicate_content"] = sum(
            bool(
                entry.sha256
                and m.SourceVersion.objects.using(using)
                .filter(sha256=entry.sha256)
                .exclude(source_file__relative_path=entry.relative_path)
                .exists()
            )
            for entry in entries
        )
        record.save(using=using)


def run(context):
    scan = _scan(context)
    with ExitStack() as stack:
        roots = p._open_roots(stack, context.using)
        # STATUS is independently validated before any indexing write.
        from apps.archive.status import open_status, publish_status

        status = stack.enter_context(open_status(roots))
        processor = p._processor(roots["DATA"], context.checkpoint)
        if not scan.inventory_ready:
            try:
                observed = inventory.scan(roots["RAW"], scan.selected_path, checkpoint=context.checkpoint)
            except (files.FileError, OSError, ValueError):
                context.commit_metadata(
                    lambda: m.IndexScan.objects.using(context.using)
                    .filter(pk=scan.pk)
                    .update(error_code="INVENTORY_FAILED")
                )
                raise
            context.commit_metadata(lambda: _record_inventory(scan, observed, context.using))
        entries = scan.entries.using(context.using).order_by("relative_path")
        total = entries.count()
        for number, entry in enumerate(entries.iterator(), 1):
            context.checkpoint(min(85, int(number * 85 / max(1, total))))
            if entry.state == "PENDING":
                _entry(context, entry, roots, processor)
        if not scan.folders.using(context.using).exclude(snapshot={}).exists():
            current = inventory.scan(roots["RAW"], scan.selected_path, checkpoint=context.checkpoint)
            expected = {entry.relative_path: entry.fingerprint for entry in scan.entries.using(context.using)}
            actual = {item["path"]: item["fingerprint"] for item in current if item["kind"] != "DIRECTORY"}
            if actual != expected:

                def incomplete():
                    m.IndexScan.objects.using(context.using).filter(pk=scan.pk).update(error_code="SOURCE_CHANGED")
                    m.SourceFolder.objects.using(context.using).filter(index_history__scan=scan).update(
                        index_state="PARTIAL_FAILURE"
                    )

                context.commit_metadata(incomplete)
                raise files.FileError("SOURCE_CHANGED")
            context.commit_metadata(lambda: _summarize(context, scan))
        for record in scan.folders.using(context.using):
            publish_status(context, status, record)
        context.commit_metadata(
            lambda: m.IndexScan.objects.using(context.using).filter(pk=scan.pk).update(completed=True)
        )


def acknowledge(context, intent):
    if intent.key.startswith("archive-publish:"):
        operation = m.FileOperation.objects.using(context.using).get(
            pk=intent.payload["operation_id"], job_id=context.job_id
        )
        p.acknowledge(CopyContext(context, operation), intent)


def reconcile(context, intent):
    if intent.key.startswith("archive-publish:"):
        operation = m.FileOperation.objects.using(context.using).get(
            pk=intent.payload["operation_id"], job_id=context.job_id
        )
        return p.reconcile(CopyContext(context, operation), intent)
    from apps.archive.status import reconcile_status

    return reconcile_status(context, intent)


def register():
    queue.HANDLERS[Job.Kind.INDEX_SCAN] = queue.Handler(
        validate_payload,
        run,
        idempotent=True,
        max_attempts=3,
        reconcile=reconcile,
        acknowledge=acknowledge,
        recover_cleanup=p.recover_cleanup,
    )
