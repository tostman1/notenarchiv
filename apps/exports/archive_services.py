"""Minimal immutable archive print selection; no fake project or participant."""

import tempfile
import time
from pathlib import Path
from uuid import UUID, uuid4

from django.conf import settings
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from apps.archive.download_services import files, signature
from apps.archive.library_services import verify_file
from apps.exports.models import GenerationRun, GenerationSnapshot, SnapshotInput
from apps.jobs.services import queue
from apps.projects.preflight_services import fingerprint, inspect_file
from apps.projects.services import reviewer

SALT = "exports.archive-generation.v1"


def report(identifiers):
    selected = files(identifiers)
    if sum(f.byte_size for f in selected) > 104_857_600 or any(not verify_file(f) for f in selected):
        raise ValidationError(_("Archiv-Auswahl ungültig, beschädigt oder zu groß."))
    deadline = time.monotonic() + 60
    try:
        with tempfile.TemporaryDirectory(
            prefix="archive-print-", dir=Path(settings.DIAGNOSTIC_LOG_DIR).parent
        ) as scratch:
            for file in selected:
                if time.monotonic() > deadline:
                    raise ValueError("Inspection deadline exceeded")
                inspect_file(file, Path(scratch), deadline)
    except (ValueError, OSError):
        raise ValidationError(_("Archiv-PDF unlesbar oder Prüfgrenze überschritten.")) from None
    return selected


def token(selected, actor):
    return signing.dumps(
        {"files": signature(selected), "actor": str(actor.pk), "request": str(uuid4())}, salt=SALT, compress=True
    )


def authorize(identifiers, authorization, actor, variant="PRINT"):
    actor = reviewer(actor)
    try:
        value = signing.loads(authorization, salt=SALT, max_age=1800)
    except signing.BadSignature:
        raise ValidationError(_("Archiv-Freigabe abgelaufen oder ungültig.")) from None
    selected = report(identifiers)
    try:
        UUID(value["request"])
    except (KeyError, ValueError, TypeError):
        raise ValidationError(_("Ungültige Archiv-Freigabe.")) from None
    if (
        value.get("files") != signature(selected)
        or value.get("actor") != str(actor.pk)
        or variant not in {"READING", "PRINT"}
    ):
        raise ValidationError(_("Archiv-Auswahl geändert; erneut prüfen."))
    entries = [
        {**c, "ordinal": i + 1, "title": str(f.arrangement)}
        for i, (f, c) in enumerate(zip(selected, signature(selected), strict=True))
    ]
    payload = {
        "schema": 1,
        "project": "None",
        "revision": 0,
        "project_name": "Einzelnoten",
        "blocking": 0,
        "positions": [],
        "participants": [],
        "cells": [],
        "dependencies": {},
        "archive_files": entries,
        "output_variant": variant,
        "options": {"layout": "REGULAR", "cover_enabled": False, "cover_title": "", "width_mm": 210, "height_mm": 297},
    }
    with transaction.atomic():
        # Short writer acquisition and metadata eligibility recheck, no PDF I/O.
        from django.db.models import F

        from apps.archive.models import ArchiveFile

        ArchiveFile.objects.filter(pk=selected[0].pk).update(revision=F("revision"))
        if signature(files(identifiers)) != signature(selected):
            raise ValidationError(_("Archiv-Eingaben während Freigabe geändert."))
        existing = GenerationSnapshot.objects.filter(request_id=value["request"]).first()
        if existing:
            if existing.sha256 != fingerprint(payload) or existing.actor_id != actor.pk:
                raise ValidationError(_("Freigabe bereits anders verwendet."))
            return existing.run
        snapshot = GenerationSnapshot.objects.create(
            request_id=value["request"],
            project_revision=0,
            kind="ARCHIVE_NOTES",
            payload=payload,
            sha256=fingerprint(payload),
            preflight_sha256=fingerprint(payload),
            actor=actor,
        )
        for file, cell in zip(selected, entries, strict=True):
            assignment = file.assignments.usable().order_by("pk").first()
            SnapshotInput.objects.create(
                snapshot=snapshot,
                ordinal=cell["ordinal"],
                part_id=assignment.part_id,
                assignment=assignment,
                archive_file=file,
                source_version_id=file.source_version_id,
                sha256=file.sha256,
                byte_size=file.byte_size,
                file_revision=file.revision,
            )
        job = queue.enqueue("GENERATE", {"snapshot_id": str(snapshot.pk), "sha256": snapshot.sha256})
        return GenerationRun.objects.create(snapshot=snapshot, job=job)
