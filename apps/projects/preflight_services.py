"""Read-only pre-generation inspection using the single central resolver."""

import hashlib
import json
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from uuid import UUID, uuid4

from django.conf import settings
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from apps.archive import library_services
from apps.archive import models as archive
from apps.exports.dependencies import dependency_payload
from apps.projects.matrix_services import cell_context
from apps.projects.resolution_services import ResolutionSession, bounded
from core import preview
from core.locking import ProcessLock
from core.pdf import Limits, PdfError, Processor

MAX_CELLS = 5000
MAX_FILES = 128
MAX_BYTES = 512 * 1024**2
MAX_SECONDS = 60
SALT = "projects.preflight.v1"
LAYOUT_LABELS = {
    "NATIVE_A3": _("Native A3-Seite bleibt vollständig erhalten."),
    "LANDSCAPE": _("Querformat bleibt erhalten; Drucklayout später gesondert prüfen."),
    "ROTATED": _("Gedrehte Seite: Orientierung in der Vorschau prüfen."),
    "CUSTOM": _("Sonderformat bleibt erhalten; Druckmedium gesondert prüfen."),
    "CROP": _("Abweichender Seitenrahmen: sichtbaren Bereich in der Vorschau prüfen."),
    "MIXED": _("Gemischte Seitenformate innerhalb einer Ausgabe."),
}


def fingerprint(payload):
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


@dataclass
class PreflightReport:
    session: ResolutionSession
    rows: list
    payload: dict
    missing_keys: set
    blocking: int

    @property
    def digest(self):
        return fingerprint(self.payload)


def inspect_file(file, scratch, deadline):
    data = preview.snapshot(
        settings.CURATED_DIR if file.root_kind == "CLEAN" else settings.PROCESSED_DIR,
        file.relative_path,
        maximum=min(settings.PDF_MAX_BYTES, 104_857_600),
        sha256=file.sha256,
        size=file.byte_size,
    )
    remaining = max(1, min(30, int(deadline - time.monotonic())))
    with ProcessLock(Path(settings.DIAGNOSTIC_LOG_DIR).parent / "preview-render.lock"):
        info = Processor(scratch, limits=Limits(timeout_seconds=remaining)).inspect(data)
    flags = set()
    papers = set()
    for page in info.pages:
        papers.add(page.paper)
        if page.paper == "A3":
            flags.add("NATIVE_A3")
        if page.width_points > page.height_points:
            flags.add("LANDSCAPE")
        if page.rotation:
            flags.add("ROTATED")
        if page.paper == "CUSTOM":
            flags.add("CUSTOM")
        if page.crop_box != page.media_box or page.user_unit != 1:
            flags.add("CROP")
    if len(papers) > 1:
        flags.add("MIXED")
    return {"pages": [asdict(page) for page in info.pages], "flags": sorted(flags)}


def build_report(project_id, *, participant_ids=None, position_ids=None):
    try:
        participant_ids = None if participant_ids is None else [UUID(str(value)) for value in participant_ids]
        position_ids = None if position_ids is None else [UUID(str(value)) for value in position_ids]
    except (ValueError, TypeError):
        raise ValidationError(_("Ungültige Person oder Position.")) from None
    for selected in (participant_ids, position_ids):
        if selected is not None and len(selected) != len(set(selected)):
            raise ValidationError(_("Personen und Positionen nicht mehrfach auswählen."))
    with transaction.atomic():
        session = ResolutionSession(project_id, participant_ids=participant_ids, position_ids=position_ids)
        dependencies = dependency_payload(session)
        if not session.participants or not session.positions:
            raise ValidationError(_("Mindestens eine aktive Person und Position auswählen."))
        if len(session.participants) * len(session.positions) > MAX_CELLS:
            raise ValidationError(_("Vorprüfung auf höchstens 5.000 Zuordnungen begrenzen."))
        arrangements = {row.arrangement_id for row in session.positions.values() if row.arrangement_id}
        pending = bounded(
            library_services.pending_files()
            .filter(
                Q(current_proposal__arrangement_id__in=arrangements)
                | Q(current_proposal__isnull=True, candidates__proposed_arrangement_id__in=arrangements)
            )
            .distinct()
            .order_by("pk")
            .values("pk", "revision", "candidate_state", "current_proposal__arrangement_id"),
            2000,
        )
        unavailable = set(
            bounded(
                archive.ArchiveAssignment.objects.filter(
                    archive_file__arrangement_id__in=arrangements,
                    archive_file__review_state="CONFIRMED",
                    archive_file__publication_state__in=["MISSING", "CORRUPT"],
                ).values_list("archive_file__arrangement_id", "part_id"),
                2000,
            )
        )
    deadline, total_bytes, documents = time.monotonic() + MAX_SECONDS, 0, {}
    rows, missing_keys, blocking = [], set(), 0
    root = Path(settings.DIAGNOSTIC_LOG_DIR).parent
    with tempfile.TemporaryDirectory(prefix="preflight-", dir=root) as directory:
        scratch = Path(directory)
        for position in session.positions.values():
            cells = []
            for person in session.participants.values():
                if time.monotonic() > deadline:
                    raise ValidationError(_("Prüfzeit überschritten; weniger Positionen auswählen."))
                result = session.verified_resolution(position.pk, person.pk)
                inspection = None
                if result.usable:
                    file = session.assignments[result.assignment_id].archive_file
                    if file.pk not in documents:
                        total_bytes += file.byte_size
                        if len(documents) >= MAX_FILES or total_bytes > MAX_BYTES:
                            raise ValidationError(_("Prüfumfang überschritten; weniger Positionen auswählen."))
                        try:
                            documents[file.pk] = inspect_file(file, scratch, deadline)
                        except (PdfError, OSError, ValueError):
                            documents[file.pk] = {"error": "UNREADABLE_PDF"}
                    inspection = documents[file.pk]
                key = f"{position.pk}:{person.pk}"
                failure = result.status not in {"AVAILABLE", "SUBSTITUTED", "RESERVE", "MISSING"}
                failure = failure or bool(inspection and inspection.get("error"))
                unavailable_input = (
                    result.status == "MISSING" and (position.arrangement_id, result.desired_part_id) in unavailable
                )
                failure = failure or unavailable_input
                if failure:
                    blocking += 1
                if result.status == "MISSING" and not failure:
                    missing_keys.add(key)
                cell = cell_context(session, result)
                cell.update(
                    key=key,
                    blocking=failure,
                    inspection=inspection,
                    missing=result.status == "MISSING" and not failure,
                    unavailable_input=unavailable_input,
                    person=person,
                    layout_flags=[LAYOUT_LABELS[flag] for flag in (inspection or {}).get("flags", [])],
                )
                cells.append(cell)
            rows.append({"position": position, "cells": cells})
    project = session.project
    payload = {
        "schema": 1,
        "dependencies": dependencies,
        "project_name": project.name,
        "project": str(project.pk),
        "revision": project.revision,
        "options": {
            "layout": project.layout,
            "width_mm": project.width_mm,
            "height_mm": project.height_mm,
            "cover_enabled": project.cover_enabled,
            "cover_title": project.cover_title,
        },
        "participants": [
            {
                "id": str(p.pk),
                "name": p.display_name,
                "part": str(p.default_part_id),
                "role": str(p.role_id) if p.role_id else None,
            }
            for p in session.participants.values()
        ],
        "positions": [
            {
                "id": str(p.pk),
                "order": p.order,
                "arrangement": str(p.arrangement_id),
                "title": str(p.arrangement) if p.arrangement_id else "Reserve",
            }
            for p in session.positions.values()
        ],
        "cells": [asdict(cell["resolution"]) for row in rows for cell in row["cells"]],
        "documents": {str(key): value for key, value in documents.items()},
        "pending": pending,
        "unavailable": sorted((str(arr), str(part)) for arr, part in unavailable),
        "blocking": blocking,
    }
    # UUIDs are canonical strings, including nested resolver and pending identities.
    payload = json.loads(json.dumps(payload, default=str))
    return PreflightReport(session, rows, payload, missing_keys, blocking)


def report_token(report, actor):
    return signing.dumps(
        {
            "project": str(report.session.project.pk),
            "actor": str(actor.pk),
            "digest": report.digest,
            "request_id": str(uuid4()),
        },
        salt=SALT,
        compress=True,
    )


def validate_acknowledgement(report, token, acknowledgements, actor):
    try:
        value = signing.loads(token, salt=SALT, max_age=1800)
    except signing.BadSignature:
        raise ValidationError(_("Vorprüfung abgelaufen oder ungültig; erneut prüfen.")) from None
    if (
        value.get("project") != str(report.session.project.pk)
        or value.get("actor") != str(actor.pk)
        or value.get("digest") != report.digest
    ):
        raise ValidationError(_("Projekt oder Eingaben geändert; Vorprüfung erneut durchführen."))
    try:
        UUID(value["request_id"])
    except (ValueError, KeyError, TypeError):
        raise ValidationError(_("Ungültige Vorprüfungsfreigabe.")) from None
    if report.blocking:
        raise ValidationError(_("Blockierende Fehler zuerst korrigieren; keine Freigabe möglich."))
    if set(acknowledgements) != report.missing_keys or len(acknowledgements) != len(set(acknowledgements)):
        raise ValidationError(_("Jede fehlende Zuordnung ausdrücklich als Platzhalter bestätigen."))
    return True
