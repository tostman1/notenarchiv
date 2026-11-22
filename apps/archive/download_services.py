"""Explicit immutable archive note selections; no project or member dependency."""

import time
from pathlib import Path
from uuid import UUID

from django.conf import settings
from django.core import signing
from django.core.exceptions import ValidationError

from apps.archive import models as m
from core import downloads
from core.files import FileError
from core.locking import ProcessLock

SALT = "archive.direct-download.v1"


class SelectionChanged(ValidationError):
    pass


def files(identifiers):
    if not 1 <= len(identifiers) <= downloads.MAX_FILES:
        raise ValidationError("Invalid download selection.")
    try:
        ids = [UUID(str(value)) for value in identifiers]
    except (ValueError, TypeError):
        raise ValidationError("Invalid edition identifier.") from None
    if len(set(ids)) != len(ids):
        raise ValidationError("Duplicate edition selection; each combined PDF is exported once.")
    found = {
        file.pk: file
        for file in m.ArchiveFile.objects.usable()
        .filter(pk__in=ids, assignments__in=m.ArchiveAssignment.objects.usable())
        .select_related("source_version", "publication_operation__intent")
        .prefetch_related("assignments__part__instrument", "arrangement__work")
        .distinct()
    }
    if len(found) != len(ids):
        raise ValidationError("Selected edition is not confirmed and available.")
    result = [found[identifier] for identifier in ids]
    if sum(file.byte_size for file in result) > downloads.MAX_TOTAL:
        raise ValidationError("Download byte limit exceeded.")
    if any(not 0 < file.byte_size <= min(settings.PDF_MAX_BYTES, downloads.MAX_FILE) for file in result):
        raise ValidationError("PDF byte limit exceeded.")
    for file in result:
        file.full_clean()
        operation = file.publication_operation
        if (
            operation.intent.result != operation.expected_receipt
            or operation.intent.payload != operation.effect_payload
        ):
            raise ValidationError("Publication evidence is invalid.")
    return result


def signature(selected):
    return [
        {
            "id": str(file.pk),
            "revision": file.revision,
            "hash": file.sha256,
            "size": file.byte_size,
            "root": file.root_kind,
            "path": file.relative_path,
            "arrangement": str(file.arrangement_id),
        }
        for file in selected
    ]


def selection_token(selected, actor):
    return signing.dumps({"actor": str(actor.pk), "files": signature(selected)}, salt=SALT, compress=True)


def from_token(token, actor):
    if not isinstance(token, str) or len(token) > 32_768:
        raise SelectionChanged("Invalid selection token.")
    try:
        payload = signing.loads(token, salt=SALT, max_age=900)
        if payload["actor"] != str(actor.pk):
            raise ValueError
        selected = files([entry["id"] for entry in payload["files"]])
        if signature(selected) != payload["files"]:
            raise ValueError
    except (signing.BadSignature, KeyError, TypeError, ValueError, ValidationError):
        raise SelectionChanged("Selection changed or expired; select again.") from None
    return selected


class StagedDownload:
    def __init__(self, stream, lock):
        self.stream, self.lock = stream, lock
        self.deadline = time.monotonic() + 120

    def __getattr__(self, name):
        if name == "fileno":
            raise AttributeError(name)  # Prevent sendfile/file-wrapper bypass of the bounded read method.
        return getattr(self.stream, name)

    def read(self, *args):
        if time.monotonic() > self.deadline:
            self.close()
            return b""  # Stop a stalled response, never retry or substitute bytes.
        return self.stream.read(*args)

    def close(self):
        if not self.stream.closed:
            try:
                self.stream.close()
            finally:
                self.lock.__exit__()


def stage(selected, *, zipped):
    parent = Path(settings.DIAGNOSTIC_LOG_DIR).parent
    for root in (
        settings.SOURCE_DIR,
        settings.CURATED_DIR,
        settings.PROCESSED_DIR,
        settings.STATUS_DIR,
        settings.EXPORT_DIR,
    ):
        if parent.resolve().is_relative_to(Path(root).resolve()) or Path(root).resolve().is_relative_to(
            parent.resolve()
        ):
            raise FileError("UNSAFE_STAGING")
    scratch = downloads.scratch_directory(parent)
    lock = ProcessLock(parent / "direct-download.lock")
    lock.__enter__()
    stream = None
    try:
        inputs = [
            downloads.Input(
                root=Path(settings.CURATED_DIR if file.root_kind == "CLEAN" else settings.PROCESSED_DIR),
                path=file.relative_path,
                sha256=file.sha256,
                size=file.byte_size,
                filename=f"note-{file.pk}.pdf",
            )
            for file in selected
        ]
        stream = downloads.build(inputs, scratch, zipped=zipped)
        # Catch review/availability changes during physical preparation before
        # response headers. Once returned, only staged immutable bytes are read.
        try:
            current = files([file.pk for file in selected])
        except ValidationError:
            raise SelectionChanged("Selection changed during download preparation.") from None
        if signature(current) != signature(selected):
            raise SelectionChanged("Selection changed during download preparation.")
        return StagedDownload(stream, lock)
    except BaseException:
        if stream is not None:
            stream.close()
        lock.__exit__()
        raise
