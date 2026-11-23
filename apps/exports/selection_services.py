"""Contents-only and exact historical excerpt authorization, with immutable pins."""

import copy
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4

from django.conf import settings
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils.translation import gettext_lazy as _

from apps.exports.models import GenerationRun, GenerationSnapshot, SnapshotInput, SnapshotParticipant, SnapshotPosition
from apps.jobs.services import queue
from apps.projects.models import Project
from apps.projects.preflight_services import fingerprint, inspect_file
from apps.projects.services import reviewer

SALT = "exports.selection.v1"


@dataclass
class SelectionReport:
    payload: dict
    source: GenerationSnapshot | None = None

    @property
    def digest(self):
        return fingerprint(self.payload)

    @property
    def missing(self):
        return sorted(
            f"{c['position_id']}:{c['participant_id']}" for c in self.payload["cells"] if c["status"] == "MISSING"
        )


def contents_report(project_id):
    with transaction.atomic():
        project = Project.objects.get(pk=project_id)
        positions = list(
            project.positions.filter(active=True).select_related("arrangement__work").order_by("order")[:1001]
        )
        if not 1 <= len(positions) <= 1000 or project.status != "ACTIVE":
            raise ValidationError(_("Aktives Projekt mit mindestens einer gemeinsamen Position erforderlich."))
        payload = {
            "schema": 1,
            "project": str(project.pk),
            "revision": project.revision,
            "project_name": project.name,
            "blocking": 0,
            "participants": [],
            "cells": [],
            "dependencies": {},
            "options": {
                "layout": project.layout,
                "width_mm": project.width_mm,
                "height_mm": project.height_mm,
                "cover_enabled": False,
                "cover_title": "",
            },
            "positions": [
                {
                    "id": str(p.pk),
                    "order": p.order,
                    "arrangement": str(p.arrangement_id),
                    "title": str(p.arrangement) if p.arrangement_id else "Reserve",
                }
                for p in positions
            ],
        }
    return SelectionReport(payload)


def historical_report(source_id, participant_ids, position_ids):
    source = GenerationSnapshot.objects.get(pk=source_id)
    source.full_clean()
    if source.kind not in {"FULL", "EXCERPT"}:
        raise ValidationError(_("Diese Ausgabe enthält keine persönlichen Noten."))
    try:
        people, positions = [[str(UUID(str(v))) for v in values] for values in (participant_ids, position_ids)]
    except (ValueError, TypeError):
        raise ValidationError(_("Ungültige historische Auswahl.")) from None
    if (
        not people
        or not positions
        or len(people) != len(set(people))
        or len(positions) != len(set(positions))
        or not set(people) <= {p["id"] for p in source.payload["participants"]}
        or not set(positions) <= {p["id"] for p in source.payload["positions"]}
    ):
        raise ValidationError(_("Historische Personen oder Positionen fehlen oder sind fremd."))
    payload = copy.deepcopy(source.payload)
    payload["participants"] = [p for p in payload["participants"] if p["id"] in people]
    payload["positions"] = [p for p in payload["positions"] if p["id"] in positions]
    payload["cells"] = [c for c in payload["cells"] if c["participant_id"] in people and c["position_id"] in positions]
    payload["historical_source"] = {"id": str(source.pk), "sha256": source.sha256}
    payload["options"]["cover_enabled"] = False
    if not any(c["status"] != "RESERVE" for c in payload["cells"]):
        raise ValidationError(_("Reserven enthalten keine Noten für einen Auszug."))
    from apps.archive.library_services import verify_file

    selected = {
        (c["position_id"], c["participant_id"]): c
        for c in payload["cells"]
        if c["status"] in {"AVAILABLE", "SUBSTITUTED"}
    }
    pins = list(
        source.inputs.filter(position_id__in=positions, participant_id__in=people).select_related(
            "archive_file__publication_operation__intent", "assignment", "source_version"
        )
    )
    if len(pins) != len(selected):
        raise ValidationError(_("Historische Eingaben unvollständig."))
    verified = set()

    scratch_root = Path(settings.DIAGNOSTIC_LOG_DIR).parent
    deadline = time.monotonic() + 60
    total = 0
    for pin in pins:
        cell = selected.get((str(pin.position_id), str(pin.participant_id)))
        if not cell or any(
            str(getattr(pin, field)) != str(cell[key])
            for field, key in (
                ("archive_file_id", "file_id"),
                ("assignment_id", "assignment_id"),
                ("part_id", "effective_part_id"),
                ("sha256", "sha256"),
                ("byte_size", "byte_size"),
                ("source_version_id", "source_version_id"),
                ("file_revision", "file_revision"),
            )
        ):
            raise ValidationError(_("Historische Eingaben geändert."))
        if (
            pin.assignment.state != "CONFIRMED"
            or pin.assignment.part_id != pin.part_id
            or pin.assignment.archive_file_id != pin.archive_file_id
            or pin.archive_file.revision != pin.file_revision
            or pin.archive_file.sha256 != pin.sha256
            or pin.archive_file.byte_size != pin.byte_size
        ):
            raise ValidationError(_("Historische Zuordnung nicht mehr gültig oder freigegeben."))
        if pin.archive_file_id not in verified:
            total += pin.byte_size
            if len(verified) >= 128 or total > 512 * 1024**2 or time.monotonic() > deadline:
                raise ValidationError(_("Historischen Prüfumfang reduzieren; Prüfgrenze überschritten."))
            if not verify_file(pin.archive_file):
                raise ValidationError(_("Historische Datei fehlt, ist beschädigt oder nicht freigegeben."))
            try:
                with tempfile.TemporaryDirectory(prefix="historical-", dir=scratch_root) as scratch:
                    inspect_file(pin.archive_file, Path(scratch), deadline)
            except (ValueError, OSError):
                raise ValidationError(_("Historische PDF-Datei unlesbar oder Prüfgrenze überschritten.")) from None
            verified.add(pin.archive_file_id)
    return SelectionReport(payload, source)


def selection_token(report, actor):
    return signing.dumps({"digest": report.digest, "actor": str(actor.pk), "request_id": str(uuid4())}, salt=SALT)


def authorize_selection(report, token, acknowledgements, actor):
    actor = reviewer(actor)
    try:
        value = signing.loads(token, salt=SALT, max_age=1800)
    except signing.BadSignature:
        raise ValidationError(_("Freigabe abgelaufen oder ungültig; erneut prüfen.")) from None
    if (
        value.get("digest") != report.digest
        or value.get("actor") != str(actor.pk)
        or sorted(acknowledgements) != report.missing
    ):
        raise ValidationError(_("Auswahl geändert oder fehlende Noten nicht vollständig bestätigt."))
    try:
        UUID(value["request_id"])
    except (KeyError, ValueError, TypeError):
        raise ValidationError(_("Ungültige Generierungsfreigabe.")) from None
    if report.source:
        # Verify only immutable historical inputs, never current assignment defaults.
        checked = historical_report(
            report.source.pk,
            [p["id"] for p in report.payload["participants"]],
            [p["id"] for p in report.payload["positions"]],
        )
        if checked.digest != report.digest:
            raise ValidationError(_("Historische Eingaben geändert; erneut prüfen."))
    with transaction.atomic():
        if report.source is None:
            if not Project.objects.filter(
                pk=report.payload["project"], revision=report.payload["revision"], status="ACTIVE"
            ).update(revision=F("revision")):
                raise ValidationError(_("Projekt geändert; erneut prüfen."))
            if contents_report(report.payload["project"]).digest != report.digest:
                raise ValidationError(_("Inhaltsverzeichnis geändert; erneut prüfen."))
        else:
            # Acquire the SQLite writer without re-resolving project assignments.
            Project.objects.filter(pk=report.payload["project"]).update(revision=F("revision"))
        existing = GenerationSnapshot.objects.filter(request_id=value["request_id"]).first()
        if existing:
            if existing.sha256 != report.digest or existing.actor_id != actor.pk:
                raise ValidationError(_("Freigabe bereits anders verwendet."))
            return existing.run
        snapshot = GenerationSnapshot.objects.create(
            request_id=value["request_id"],
            project_id=report.payload["project"],
            project_revision=report.payload["revision"],
            kind="EXCERPT" if report.source else "CONTENTS",
            payload=report.payload,
            sha256=report.digest,
            preflight_sha256=report.digest,
            actor=actor,
            acknowledgements=report.missing,
            source_snapshot=report.source,
        )
        for p in report.payload["positions"]:
            SnapshotPosition.objects.create(
                snapshot=snapshot,
                position_id=p["id"],
                number=p["order"],
                title=p["title"],
                arrangement_id=None if p["arrangement"] == "None" else p["arrangement"],
            )
        if report.source:
            people = {p["id"] for p in report.payload["participants"]}
            positions = {p["id"] for p in report.payload["positions"]}
            for pin in report.source.participants.all():
                if str(pin.participant_id) in people:
                    SnapshotParticipant.objects.create(
                        snapshot=snapshot,
                        participant_id=pin.participant_id,
                        default_part_id=pin.default_part_id,
                        role_id=pin.role_id,
                        display_name=pin.display_name,
                    )
            for pin in report.source.inputs.all():
                if str(pin.participant_id) in people and str(pin.position_id) in positions:
                    fields = {
                        f.attname: getattr(pin, f.attname)
                        for f in pin._meta.fields
                        if f.name not in {"id", "created_at", "snapshot"}
                    }
                    SnapshotInput.objects.create(snapshot=snapshot, **fields)
        job = queue.enqueue("GENERATE", {"snapshot_id": str(snapshot.pk), "sha256": snapshot.sha256})
        return GenerationRun.objects.create(snapshot=snapshot, job=job)
