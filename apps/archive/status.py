"""Regenerable, fenced STATUS mirror. Unknown marker files are never replaced."""

import hashlib
import json
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
        if files.identity(root.root_metadata()) in {files.identity(other.root_metadata()) for other in roots.values()}:
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
        written = root.write_stage(stage_path, (data,), maximum=16_384, checkpoint=context.checkpoint)
        identity = files.identity(written)
        staged_data, staged_info = root.read(stage_path, maximum=16_384, checkpoint=context.checkpoint)
        if staged_data != data or files.identity(staged_info) != identity:
            raise files.FileError("STATUS_CONFLICT")
        root.prepare_parent(path)

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
                root.publish_marker(
                    stage_path,
                    path,
                    expected_identity=identity,
                    previous=previous,
                    temporary=".index-status-" + identifier.hex,
                )
                return {"sha256": payload["sha256"], "size": len(data)}
            except files.MarkerConflict as error:
                raise lifecycle.NoEffect(f"STATUS publication conflict ({error.code})") from None

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
