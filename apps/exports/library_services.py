"""Read-only artifact classification: current scope differs from historical integrity."""

import time
from dataclasses import dataclass
from uuid import UUID

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from apps.archive.library_services import verify_file
from apps.exports.generation import is_complete
from apps.projects.resolution_services import ResolutionSession
from core import preview

REASONS = {
    "PIECE_LIST_CHANGED": _("Gemeinsame Stückliste, Nummern oder Titel geändert."),
    "PARTICIPANT_REMOVED": _("Diese Person ist nicht mehr aktiv im Projekt ausgewählt."),
    "POSITION_REMOVED": _("Eine exportierte Position wurde entfernt oder ersetzt."),
    "PART_ASSIGNMENT_CHANGED": _("Persönliche oder effektive Stimmzuordnung geändert."),
    "EDITION_CHANGED": _("Konkrete Ausgabe oder Bevorzugung geändert."),
    "ROLE_OR_RULE_CHANGED": _("Relevante Rolle, Ensemble-Zuordnung oder Ersatzregel geändert."),
    "CATALOG_CHANGED": _("Relevante Werk-, Stimmen- oder Notationsdaten geändert."),
    "PROJECT_OPTIONS_CHANGED": _("Relevanter Projektname, Deckblatt oder Seitenoptionen geändert."),
    "PARTICIPANT_METADATA_CHANGED": _("Name oder gespeicherte Deckblatt-Zuordnung dieser Person geändert."),
    "INPUT_UNAVAILABLE": _("Eine exakt gespeicherte Notendatei fehlt, ist beschädigt oder nicht freigegeben."),
    "SOURCE_PRESENCE_CHANGED": _("RAW-Quellstatus geändert; gespeicherte CLEAN-Kopie wird separat geprüft."),
    "CLASSIFICATION_LIMIT": _("Aktueller Vergleich nicht vollständig möglich; gezielt prüfen."),
}


@dataclass(frozen=True)
class Classification:
    output: str
    stale_reasons: tuple[str, ...]
    reproducible: bool
    input_reasons: tuple[str, ...] = ()

    @property
    def stale(self):
        return bool(self.stale_reasons)

    @property
    def reason_labels(self):
        return [REASONS[r] for r in self.stale_reasons]

    @property
    def input_labels(self):
        return [REASONS[r] for r in self.input_reasons]

    @property
    def output_label(self):
        return {
            "VERIFIED": _("Datei vollständig und hash-geprüft"),
            "UNAVAILABLE": _("Datei fehlt oder ist beschädigt"),
            "INCOMPLETE": _("Auftrag nicht vollständig erfolgreich"),
            "UNCHECKED": _("Prüfumfang überschritten; gezielte Auswahl prüfen"),
            "BATCH_UNAVAILABLE": _("Andere Datei dieses Auftrags fehlt oder ist beschädigt; Batch gesperrt"),
        }[self.output]


def _stable(row):
    return {k: str(v) for k, v in row.items() if k not in {"created_at", "updated_at", "revision"}}


def _catalog(snapshot, session, person, current_cells):
    old = snapshot.payload.get("dependencies", {})
    used_parts = {str(c.get(k)) for c in current_cells for k in ("desired_part_id", "effective_part_id")}
    if snapshot.kind == "FULL" and snapshot.payload["options"]["cover_enabled"]:
        used_parts.add(person["part"])
    current = {"parts": [], "instruments": [], "roles": [], "arrangements": [], "works": []}
    current["parts"] = [p for p in session.parts.values() if str(p.pk) in used_parts]
    current["instruments"] = list({p.instrument_id: p.instrument for p in current["parts"]}.values())
    current["roles"] = [p.role for p in session.participants.values() if p.role_id]
    current["arrangements"] = list(
        {p.arrangement_id: p.arrangement for p in session.positions.values() if p.arrangement_id}.values()
    )
    current["works"] = list({p.work_id: p.work for p in current["arrangements"]}.values())
    for key, objects in current.items():
        previous = {r["id"]: r for r in old.get(key, [])}
        for obj in objects:
            row = {f.attname: getattr(obj, f.attname) for f in obj._meta.fields}
            if str(obj.pk) in previous and _stable(row) != _stable(previous[str(obj.pk)]):
                return True
    return False


def stale_reasons(artifact):
    snapshot = artifact.run.snapshot
    payload = snapshot.payload
    if snapshot.kind == "ARCHIVE_NOTES":
        return ()  # Exact archive selections do not inherit current preferences.
    reasons = set()
    try:
        with transaction.atomic():
            if snapshot.kind == "CONTENTS":
                from apps.projects.models import Project

                project = Project.objects.get(pk=snapshot.project_id)
                positions = list(
                    project.positions.filter(active=True).select_related("arrangement__work").order_by("order")[:1001]
                )
                if len(positions) > 1000:
                    raise ValidationError("Classification position limit")
                current = {
                    "project_name": project.name,
                    "positions": [
                        {
                            "id": str(p.pk),
                            "order": p.order,
                            "arrangement": str(p.arrangement_id),
                            "title": str(p.arrangement) if p.arrangement_id else "Reserve",
                        }
                        for p in positions
                    ],
                    "options": {
                        "layout": project.layout,
                        "width_mm": project.width_mm,
                        "height_mm": project.height_mm,
                        "cover_enabled": False,
                        "cover_title": "",
                    },
                }
                if current["positions"] != payload["positions"]:
                    reasons.add("PIECE_LIST_CHANGED")
                if current["project_name"] != payload["project_name"] or current["options"] != payload["options"]:
                    reasons.add("PROJECT_OPTIONS_CHANGED")
                return tuple(sorted(reasons))
            person = next(p for p in payload["participants"] if p["id"] == str(artifact.participant_id))
            from apps.projects.models import Project

            project = Project.objects.get(pk=snapshot.project_id)
            selected = list(
                project.positions.filter(active=True).select_related("arrangement__work").order_by("order")[:1001]
            )
            if len(selected) > 1000:
                raise ValidationError("Classification position limit")
            wanted = {p["id"] for p in payload["positions"]}
            current_positions = [
                {
                    "id": str(p.pk),
                    "order": p.order,
                    "arrangement": str(p.arrangement_id),
                    "title": str(p.arrangement) if p.arrangement_id else "Reserve",
                }
                for p in selected
                if snapshot.kind == "FULL" or str(p.pk) in wanted
            ]
            if current_positions != payload["positions"]:
                reasons.add("PIECE_LIST_CHANGED")
            current_person = project.participants.filter(pk=artifact.participant_id, active=True).first()
            if current_person is None:
                reasons.add("PARTICIPANT_REMOVED")
                return tuple(sorted(reasons))
            if not wanted <= {str(p.pk) for p in selected}:
                reasons.add("POSITION_REMOVED")
                return tuple(sorted(reasons))
            options = payload["options"]
            if (
                project.layout != options["layout"]
                or (
                    project.layout == "MARCHBOOK"
                    and (project.width_mm, project.height_mm) != (options["width_mm"], options["height_mm"])
                )
                or (
                    snapshot.kind == "FULL"
                    and (project.cover_enabled, project.cover_title)
                    != (options["cover_enabled"], options["cover_title"])
                )
            ):
                reasons.add("PROJECT_OPTIONS_CHANGED")
            if snapshot.kind == "FULL" and project.name != payload["project_name"]:
                reasons.add("PROJECT_OPTIONS_CHANGED")
            if current_person.display_name != person["name"] or (
                snapshot.kind == "FULL"
                and options["cover_enabled"]
                and str(current_person.default_part_id) != person["part"]
            ):
                reasons.add("PARTICIPANT_METADATA_CHANGED")
            if not options.get("cover_enabled") and snapshot.kind == "FULL":
                reasons.discard("PARTICIPANT_METADATA_CHANGED")
            session = ResolutionSession(
                project.pk, participant_ids=[artifact.participant_id], position_ids=[UUID(p) for p in wanted]
            )
            cells = [c for c in payload["cells"] if c["participant_id"] == person["id"]]
            for old in cells:
                now = session.resolve(UUID(old["position_id"]), artifact.participant_id)
                if any(
                    str(getattr(now, k)) != str(old[k])
                    for k in ("desired_part_id", "effective_part_id", "part_origin", "status")
                ):
                    reasons.add("PART_ASSIGNMENT_CHANGED")
                if any(
                    str(getattr(now, k)) != str(old[k])
                    for k in ("assignment_id", "file_id", "sha256", "edition_origin")
                ):
                    reasons.add("EDITION_CHANGED")
                if str(current_person.role_id or "") != str(person["role"] or "") or any(
                    str(getattr(now, k)) != str(old[k]) for k in ("mapping_id", "rule_id", "replacement_origin")
                ):
                    reasons.add("ROLE_OR_RULE_CHANGED")
                for key, identity, collection in (
                    ("mappings", now.mapping_id, session.mappings),
                    ("local_rules", now.rule_id, session.local_rules),
                    ("global_rules", now.rule_id, session.global_rules),
                ):
                    previous = next(
                        (r for r in payload.get("dependencies", {}).get(key, []) if r["id"] == str(identity)), None
                    )
                    current_rule = next((r for r in collection if r.pk == identity), None)
                    if previous and current_rule:
                        row = {f.attname: getattr(current_rule, f.attname) for f in current_rule._meta.fields}
                        if _stable(row) != _stable(previous):
                            reasons.add("ROLE_OR_RULE_CHANGED")
                if ("SOURCE_MISSING_RETAINED_COPY" in now.warnings) != (
                    "SOURCE_MISSING_RETAINED_COPY" in old["warnings"]
                ):
                    reasons.add("SOURCE_PRESENCE_CHANGED")
            if _catalog(snapshot, session, person, cells):
                reasons.add("CATALOG_CHANGED")
            old_default = next(
                (r for r in payload.get("dependencies", {}).get("participants", []) if r["id"] == person["id"]), None
            )
            if old_default and str(current_person.default_part_id) != old_default["default_part_id"]:
                old_parts = {r["id"]: r for r in payload["dependencies"]["parts"]}
                new_part = session.parts.get(current_person.default_part_id)
                if (
                    current_person.role_id
                    and new_part
                    and person["part"] in old_parts
                    and (str(new_part.instrument_id) != old_parts[person["part"]]["instrument_id"])
                ):
                    reasons.add("ROLE_OR_RULE_CHANGED")
    except (ValidationError, ValueError, KeyError, StopIteration):
        reasons.add("CLASSIFICATION_LIMIT")
    return tuple(sorted(reasons))


def classify(artifact, *, cache=None):
    cache = cache if cache is not None else {}
    run = artifact.run
    if "deadline" not in cache:
        cache["deadline"] = time.monotonic() + 60
        cache["bytes"] = 0
    run_key = ("complete", run.pk)
    if run_key not in cache:
        cache[run_key] = is_complete(run)
    output = "INCOMPLETE"
    if cache[run_key]:
        try:
            cache["bytes"] += artifact.byte_size
            if cache["bytes"] > 512 * 1024**2 or time.monotonic() > cache["deadline"]:
                return Classification("UNCHECKED", ("CLASSIFICATION_LIMIT",), False, ("CLASSIFICATION_LIMIT",))
            preview.snapshot(
                settings.EXPORT_DIR,
                artifact.relative_path,
                maximum=artifact.byte_size,
                sha256=artifact.sha256,
                size=artifact.byte_size,
            )
            output = "VERIFIED"
            for other in run.artifacts.exclude(pk=artifact.pk):
                key = ("output", other.pk)
                if key not in cache:
                    cache["bytes"] += other.byte_size
                    if cache["bytes"] > 512 * 1024**2 or time.monotonic() > cache["deadline"]:
                        return Classification("UNCHECKED", ("CLASSIFICATION_LIMIT",), False, ("CLASSIFICATION_LIMIT",))
                    try:
                        preview.snapshot(
                            settings.EXPORT_DIR,
                            other.relative_path,
                            maximum=other.byte_size,
                            sha256=other.sha256,
                            size=other.byte_size,
                        )
                        cache[key] = True
                    except (ValueError, OSError):
                        cache[key] = False
                if not cache[key]:
                    output = "BATCH_UNAVAILABLE"
        except (ValueError, OSError):
            output = "UNAVAILABLE"
    inputs = run.snapshot.inputs.select_related("archive_file__publication_operation__intent", "assignment")
    if artifact.participant_id:
        inputs = inputs.filter(participant_id=artifact.participant_id)
    reproducible = True
    for pin in inputs[:5001]:
        key = ("input", pin.archive_file_id, pin.assignment_id, pin.sha256)
        if key not in cache:
            cache["bytes"] += pin.byte_size
            if cache["bytes"] > 512 * 1024**2 or time.monotonic() > cache["deadline"]:
                return Classification(output, ("CLASSIFICATION_LIMIT",), False, ("CLASSIFICATION_LIMIT",))
            cache[key] = (
                pin.assignment.state == "CONFIRMED"
                and pin.archive_file.sha256 == pin.sha256
                and pin.archive_file.byte_size == pin.byte_size
                and verify_file(pin.archive_file)
            )
        if not cache[key]:
            reproducible = False
    return Classification(output, stale_reasons(artifact), reproducible, () if reproducible else ("INPUT_UNAVAILABLE",))
