"""Regenerable, fenced STATUS mirror. Unknown marker files are never replaced."""

import hashlib
import json
import os
import stat
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid5

from django.conf import settings

from apps.archive import models as m
from apps.jobs.services import lifecycle
from core import files

TEXT = "Indizierung abgeschlossen. Bitte jede neue oder geänderte PDF visuell prüfen und ausdrücklich bestätigen.\n"


@contextmanager
def open_status(roots):
    path = Path(settings.STATUS_DIR)
    if any(path.is_relative_to(root.path) or root.path.is_relative_to(path) for root in roots.values()):
        raise files.FileError("OVERLAPPING_ROOTS")
    with files.Root(path, writable=True) as root:
        if files.identity(os.fstat(root.fd)) in {files.identity(os.fstat(other.fd)) for other in roots.values()}:
            raise files.FileError("OVERLAPPING_ROOTS")
        yield root


def _content(record, name):
    if name == "INDEXSTATUS.json":
        return (json.dumps(record.snapshot, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    return TEXT.encode("utf-8")


def _path(record, name):
    path = record.folder.relative_path
    return f"{path}/{name}" if path else name


def _known(root, path, record, name):
    if not root.exists(path):
        return None
    data, info = root.read(path, maximum=16_384)
    if name == "INDEXSTATUS.json":
        try:
            previous = json.loads(data)
            old_record = m.IndexFolder.objects.using(record._state.db).get(
                scan_id=previous["scan_id"], folder_id=record.folder_id
            )
            if _content(old_record, name) != data:
                raise ValueError
        except (ValueError, KeyError, m.IndexFolder.DoesNotExist):
            raise files.FileError("STATUS_CONFLICT") from None
    elif data != TEXT.encode("utf-8"):
        raise files.FileError("STATUS_CONFLICT")
    return files.fingerprint(info)


def publish_status(context, root, record):
    for name in ("INDEXSTATUS.json", "_INDIZIERT_BITTE_PRUEFEN.txt"):
        context.checkpoint()
        data = _content(record, name)
        path = _path(record, name)
        identifier = uuid5(record.pk, name)
        key = "index-status:" + str(identifier)
        payload = {
            "record_id": str(record.pk),
            "name": name,
            "sha256": hashlib.sha256(data).hexdigest(),
            "size": len(data),
            "path": path,
        }
        applied = (
            m.IndexScan.objects.using(context.using)
            .get(pk=record.scan_id)
            .job.operations.filter(key=key, state="APPLIED")
            .exists()
        )
        if applied:
            # Never silently restore a modified applied marker.
            checked, _ = root.read(path, maximum=16_384, checkpoint=context.checkpoint, links=2)
            if checked != data:
                raise files.FileError("STATUS_CONFLICT")
            intent = record.scan.job.operations.using(context.using).get(key=key)
            files.release_stage(root, f".staging/{identifier.hex}/attempt-{intent.attempt}.pdf", path)
            continue
        previous = _known(root, path, record, name)
        for number in range(1, context.attempt_number):
            old_stage = f".staging/{identifier.hex}/attempt-{number}.pdf"
            if root.exists(old_stage):
                info = root.metadata(old_stage)
                if info.st_nlink == 2:
                    files.release_stage(root, old_stage, path)
                else:
                    files.discard_stage(root, old_stage, files.identity(info))
        stage_path = f".staging/{identifier.hex}/attempt-{context.attempt_number}.pdf"
        with root.parent(stage_path, create=True) as (parent, stage_name):
            descriptor = os.open(stage_name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
            try:
                remaining = memoryview(data)
                while remaining:
                    count = os.write(descriptor, remaining)
                    if count <= 0:
                        raise files.FileError("FILE_IO")
                    remaining = remaining[count:]
                os.fchmod(descriptor, 0o440)
                os.fsync(descriptor)
                identity = files.identity(os.fstat(descriptor))
            finally:
                os.close(descriptor)
            os.fsync(parent)
        with root.parent(path, create=True):
            pass

        def apply(
            path=path,
            previous=previous,
            stage_path=stage_path,
            identity=identity,
            identifier=identifier,
            payload=payload,
            data=data,
        ):
            try:
                current = files.fingerprint(root.metadata(path)) if root.exists(path) else None
                if current != previous or root.directory_spelling(path) != path:
                    raise lifecycle.NoEffect("STATUS changed before publication")
                with root.parent(stage_path) as (stage_parent, stage_name), root.parent(path) as (parent, target):
                    info = os.stat(stage_name, dir_fd=stage_parent, follow_symlinks=False)
                    if not stat.S_ISREG(info.st_mode) or files.identity(info) != identity or info.st_nlink != 1:
                        raise lifecycle.NoEffect("STATUS staging changed")
                    if previous is None:
                        if root.collides(path):
                            raise lifecycle.NoEffect("STATUS destination exists")
                        os.link(stage_name, target, src_dir_fd=stage_parent, dst_dir_fd=parent, follow_symlinks=False)
                    else:
                        temporary = ".index-status-" + identifier.hex
                        os.link(
                            stage_name, temporary, src_dir_fd=stage_parent, dst_dir_fd=parent, follow_symlinks=False
                        )
                        os.replace(temporary, target, src_dir_fd=parent, dst_dir_fd=parent)
                    os.fsync(parent)
                return {"sha256": payload["sha256"], "size": len(data)}
            except FileExistsError:
                raise lifecycle.NoEffect("STATUS destination exists") from None

        context.publish(key, payload, apply)
        files.release_stage(root, stage_path, path)


def reconcile_status(context, intent):
    from contextlib import ExitStack

    from apps.archive import publication as p

    try:
        record = (
            m.IndexFolder.objects.using(context.using)
            .select_related("folder")
            .get(pk=intent.payload["record_id"], scan__job_id=context.job_id)
        )
        name = intent.payload["name"]
        if name not in {"INDEXSTATUS.json", "_INDIZIERT_BITTE_PRUEFEN.txt"}:
            return "REVIEW_REQUIRED", {}
        data = _content(record, name)
        path = _path(record, name)
        if intent.key != "index-status:" + str(uuid5(record.pk, name)) or intent.payload != {
            "record_id": str(record.pk),
            "name": name,
            "sha256": hashlib.sha256(data).hexdigest(),
            "size": len(data),
            "path": path,
        }:
            return "REVIEW_REQUIRED", {}
        with ExitStack() as stack:
            roots = p._open_roots(stack, context.using)
            root = stack.enter_context(open_status(roots))
            if not root.exists(path):
                return "ABANDONED", {}
            stage_path = f".staging/{uuid5(record.pk, name).hex}/attempt-{intent.attempt}.pdf"
            files.verify_published(
                root,
                path,
                sha256=intent.payload["sha256"],
                size=len(data),
                staged_path=stage_path,
                checkpoint=context.checkpoint,
                durable=True,
            )
            return "APPLIED", {"sha256": intent.payload["sha256"], "size": len(data)}
    except (files.FileError, OSError, ValueError, KeyError, m.IndexFolder.DoesNotExist):
        return "REVIEW_REQUIRED", {}
