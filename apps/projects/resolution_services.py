"""Single read-only project resolver; immutable results, request-local input snapshot.

The adapter loads one consistent SQLite read transaction, then the pure selection
method reuses archive edition and project mapping/rule components without queries.
No DB mutation, publication, preflight acknowledgement or generation endpoint.
"""

from dataclasses import dataclass, replace
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from apps.archive import edition_services, library_services
from apps.archive import models as archive
from apps.projects import ensemble_services, rule_services
from apps.projects import models as m

MAX_INPUTS = 50_000
STATUS = {
    "AVAILABLE": _("Bestätigte Ausgabe gewählt"),
    "SUBSTITUTED": _("Explizite Ersatzstimme gewählt"),
    "MISSING": _("Noten fehlen"),
    "AMBIGUOUS": _("Mehrere Ausgaben — ausdrücklich wählen"),
    "INVALID": _("Ungültige Zuordnung — ausdrücklich korrigieren"),
    "CORRUPT": _("Gewählte Kopie fehlt oder Hash stimmt nicht"),
    "MAPPING_MISSING": _("Ensemble-Mapping fehlt"),
    "RESERVE": _("Reserve — keine Notenseite"),
}
PART_ORIGINS = {
    "SAVED_DEFAULT": _("Gespeicherter Projektdefault"),
    "PERSONAL": _("Persönlicher Stück-Override"),
    "ENSEMBLE_POSITION": _("Ensemble-Positionsausnahme"),
    "ENSEMBLE_PROJECT": _("Ensemble-Projektmapping"),
    "NONE": _("Keine spielbare Zuordnung"),
}
EDITION_ORIGINS = {
    "PERSONAL": _("Persönliche exakte Ausgabe"),
    "POSITION": _("Positions-Ausgabenpräferenz"),
    "PROJECT": _("Projekt-Ausgabenpräferenz"),
    "ARCHIVE": _("Archivweite Bevorzugung"),
    "SOLE": _("Einzige passende bestätigte Ausgabe"),
    "NONE": _("Keine Ausgabenwahl"),
}


@dataclass(frozen=True)
class Resolution:
    project_id: UUID
    project_revision: int
    position_id: UUID
    participant_id: UUID
    status: str
    desired_part_id: UUID | None = None
    effective_part_id: UUID | None = None
    assignment_id: UUID | None = None
    file_id: UUID | None = None
    source_version_id: UUID | None = None
    sha256: str = ""
    byte_size: int = 0
    root_kind: str = ""
    relative_path: str = ""
    file_revision: int | None = None
    part_origin: str = "NONE"
    edition_origin: str = "NONE"
    replacement_origin: str = "NONE"
    mapping_id: UUID | None = None
    rule_id: UUID | None = None
    override_id: UUID | None = None
    preference_id: UUID | None = None
    reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    @property
    def status_label(self):
        return STATUS[self.status]

    @property
    def part_origin_label(self):
        return PART_ORIGINS[self.part_origin]

    @property
    def edition_origin_label(self):
        return EDITION_ORIGINS[self.edition_origin]

    @property
    def usable(self):
        return self.status in {"AVAILABLE", "SUBSTITUTED"}


def bounded(query, limit=MAX_INPUTS):
    rows = list(query[: limit + 1])
    if len(rows) > limit:
        raise ValidationError("Resolution input limit exceeded; narrow the requested project selection.")
    return rows


class ResolutionSession:
    """Request-local consistent inputs; reuse across cells, never persist/cache globally."""

    def __init__(self, project_id, *, position_ids=None, participant_ids=None):
        with transaction.atomic():
            self.project = m.Project.objects.get(pk=project_id)
            positions = self.project.positions.filter(active=True).select_related("arrangement__work")
            people = self.project.participants.filter(active=True).select_related("default_part__instrument", "role")
            if position_ids is not None:
                positions = positions.filter(pk__in=position_ids)
            if participant_ids is not None:
                people = people.filter(pk__in=participant_ids)
            self.positions = {row.pk: row for row in bounded(positions.order_by("order"), 1000)}
            self.participants = {row.pk: row for row in bounded(people.order_by("display_name", "pk"), 500)}
            if position_ids is not None and set(position_ids) != set(self.positions):
                raise ValidationError("Selected positions are missing, removed or foreign.")
            if participant_ids is not None and set(participant_ids) != set(self.participants):
                raise ValidationError("Selected participants are inactive or foreign.")
            arrangements = {row.arrangement_id for row in self.positions.values() if row.arrangement_id}
            self.overrides = {
                (row.position_id, row.participant_id): row
                for row in bounded(
                    m.PartOverride.objects.filter(
                        project=self.project,
                        active=True,
                        position_id__in=self.positions,
                        participant_id__in=self.participants,
                    ).select_related("desired_part__instrument")
                )
            }
            self.mappings = bounded(
                m.EnsembleMapping.objects.filter(project=self.project, active=True).select_related(
                    "role", "part__instrument", "position__arrangement__work"
                ),
                20_000,
            )
            self.local_rules = bounded(
                m.ReplacementRule.objects.filter(project=self.project, active=True).select_related(
                    "desired_part__instrument", "replacement_part__instrument", "position__arrangement__work"
                ),
                2000,
            )
            self.global_rules = bounded(
                m.GlobalReplacementRule.objects.filter(active=True).select_related(
                    "desired_part__instrument", "replacement_part__instrument"
                ),
                2000,
            )
            self.global_revision = m.GlobalRuleState.objects.get(pk=1).revision
            self.project_preferences = {
                (row.arrangement_id, row.part_id): row
                for row in bounded(
                    m.ProjectEditionPreference.objects.filter(
                        project=self.project, arrangement_id__in=arrangements, active=True
                    ),
                    10_000,
                )
            }
            self.position_preferences = {
                (row.position_id, row.part_id): row
                for row in bounded(
                    m.PositionEditionPreference.objects.filter(
                        project=self.project, position_id__in=self.positions, active=True
                    ),
                    20_000,
                )
            }
            self.archive_preferences = {
                (row.arrangement_id, row.part_id): row
                for row in bounded(archive.PreferredEdition.objects.filter(arrangement_id__in=arrangements), 10_000)
            }
            assignments = bounded(
                archive.ArchiveAssignment.objects.usable()
                .filter(archive_file__arrangement_id__in=arrangements)
                .select_related(
                    "part__instrument",
                    "archive_file__source_version__source_file",
                    "archive_file__publication_operation__intent",
                )
            )
            self.assignments = {row.pk: row for row in assignments}
            self.choices = {}
            self.parts = {}
            for assignment in assignments:
                self.choices.setdefault((assignment.archive_file.arrangement_id, assignment.part_id), []).append(
                    assignment
                )
                self.parts[assignment.part_id] = assignment.part
            for person in self.participants.values():
                self.parts[person.default_part_id] = person.default_part
            for override in self.overrides.values():
                self.parts[override.desired_part_id] = override.desired_part
            for mapping in self.mappings:
                self.parts[mapping.part_id] = mapping.part
            for rule in [*self.local_rules, *self.global_rules]:
                self.parts[rule.desired_part_id] = rule.desired_part
                self.parts[rule.replacement_part_id] = rule.replacement_part
        self._verified = {}
        self._current_assignments = {}

    def _edition(self, position, part_id, override=None):
        preference, origin, selected = None, "NONE", None
        if override is not None and override.edition_id is not None:
            selected, origin = override.edition_id, "PERSONAL"
        else:
            preference = self.position_preferences.get((position.pk, part_id))
            if preference is not None:
                if preference.needs_revalidation:
                    return None, "POSITION", preference.pk, "INVALID", ("EDITION_REVALIDATION_REQUIRED",)
                selected, origin = preference.edition_id, "POSITION"
            else:
                preference = self.project_preferences.get((position.arrangement_id, part_id))
                if preference is not None:
                    selected, origin = preference.edition_id, "PROJECT"
        archive_preference = self.archive_preferences.get((position.arrangement_id, part_id))
        result = edition_services.select_edition(
            self.choices.get((position.arrangement_id, part_id), []),
            explicit_assignment_id=selected,
            preferred_assignment_id=(archive_preference.content_edition_id or archive_preference.assignment_id)
            if archive_preference
            else None,
        )
        if origin == "NONE":
            origin = result.origin
            if origin == "ARCHIVE":
                preference = archive_preference
        status = "INVALID" if result.status == "UNAVAILABLE" else result.status
        reasons = (
            ("EXPLICIT_EDITION_UNAVAILABLE",)
            if status == "INVALID"
            else ("AMBIGUOUS_EDITIONS",)
            if status == "AMBIGUOUS"
            else ("NO_CONFIRMED_EDITION",)
            if status == "MISSING"
            else ()
        )
        return result.assignment, origin, preference.pk if preference else None, status, reasons

    def resolve(self, position_id, participant_id):
        """Pure selection over the captured graph; no queries, I/O or mutation here."""
        position, person = self.positions.get(position_id), self.participants.get(participant_id)
        if position is None or person is None:
            raise ValidationError("Resolution cell is outside the selected active project graph.")
        base = Resolution(self.project.pk, self.project.revision, position_id, participant_id, "INVALID")
        if position.arrangement_id is None:
            return replace(base, status="RESERVE")
        if not position.arrangement.active or not position.arrangement.work.active:
            return replace(base, reasons=("INACTIVE_ARRANGEMENT",))
        override = self.overrides.get((position_id, participant_id))
        if override is not None:
            base = replace(
                base, part_origin="PERSONAL", desired_part_id=override.desired_part_id, override_id=override.pk
            )
            if override.needs_revalidation:
                return replace(base, reasons=("OVERRIDE_REVALIDATION_REQUIRED",))
            part = override.desired_part
        elif person.role_id is not None:
            mapping = ensemble_services.mapping_choice(
                self.project.pk,
                person.role_id,
                person.default_part.instrument_id,
                position_id,
                mappings=self.mappings,
                role=person.role,
            )
            if mapping.status != "MAPPED":
                return replace(
                    base,
                    status="MAPPING_MISSING" if mapping.status == "MISSING" else "INVALID",
                    part_origin="ENSEMBLE_POSITION" if mapping.origin == "POSITION" else "ENSEMBLE_PROJECT",
                    reasons=("ENSEMBLE_" + mapping.status,),
                )
            part = mapping.part
            base = replace(
                base,
                desired_part_id=part.pk,
                mapping_id=mapping.mapping.pk,
                part_origin="ENSEMBLE_POSITION" if mapping.origin == "POSITION" else "ENSEMBLE_PROJECT",
            )
        else:
            part = person.default_part
            base = replace(base, desired_part_id=part.pk, part_origin="SAVED_DEFAULT")
        if not part.active or not part.instrument.active:
            return replace(base, reasons=("INACTIVE_DESIRED_PART",))
        assignment, origin, pref_id, status, reasons = self._edition(position, part.pk, override)
        base = replace(
            base,
            status=status,
            effective_part_id=part.pk,
            edition_origin=origin,
            preference_id=pref_id,
            reasons=reasons,
        )
        if status == "MISSING":
            replacement = rule_services.replacement_choice(
                self.project.pk, position_id, part.pk, local_rules=self.local_rules, global_rules=self.global_rules
            )
            if replacement.status == "INVALID":
                return replace(
                    base, status="INVALID", replacement_origin=replacement.origin, reasons=("INVALID_REPLACEMENT_RULE",)
                )
            if replacement.status == "REPLACEMENT":
                # Corrupted/directly edited graph must not make a cyclic target
                # usable. Inspect edges only for safety, never resolve a second hop.
                seen, current = {part.pk}, replacement.part.pk
                for _step in range(2001):
                    if current in seen:
                        return replace(base, status="INVALID", reasons=("CYCLIC_REPLACEMENT_RULE",))
                    seen.add(current)
                    following = rule_services.replacement_choice(
                        self.project.pk,
                        position_id,
                        current,
                        local_rules=self.local_rules,
                        global_rules=self.global_rules,
                    )
                    if following.status != "REPLACEMENT":
                        break
                    current = following.part.pk
                else:
                    return replace(base, status="INVALID", reasons=("REPLACEMENT_GRAPH_LIMIT",))
                assignment, origin, pref_id, status, reasons = self._edition(position, replacement.part.pk)
                base = replace(
                    base,
                    status="SUBSTITUTED" if status == "AVAILABLE" else status,
                    effective_part_id=replacement.part.pk,
                    rule_id=replacement.rule.pk,
                    replacement_origin=replacement.origin,
                    edition_origin=origin,
                    preference_id=pref_id,
                    reasons=reasons,
                    warnings=("EXPLICIT_PART_SUBSTITUTION",),
                )
        if assignment is not None:
            file = assignment.archive_file
            base = replace(
                base,
                assignment_id=assignment.pk,
                file_id=file.pk,
                source_version_id=file.source_version_id,
                sha256=file.sha256,
                byte_size=file.byte_size,
                root_kind=file.root_kind,
                relative_path=file.relative_path,
                file_revision=file.revision,
                warnings=base.warnings
                + (("SOURCE_MISSING_RETAINED_COPY",) if file.source_version.source_file.presence == "MISSING" else ()),
            )
        return base

    def verified_resolution(self, position_id, participant_id):
        """Byte-verified boundary for matrix/preflight callers, once per file/session."""
        result = self.resolve(position_id, participant_id)
        if result.assignment_id is not None:
            state = self.assignment_state(result.assignment_id)
            if state == "CHANGED":
                return replace(result, status="INVALID", assignment_id=None, reasons=("ARCHIVE_SELECTION_CHANGED",))
            if state != "VERIFIED":
                return replace(result, status="CORRUPT", assignment_id=None, reasons=("INPUT_INTEGRITY_FAILURE",))
        return result

    def assignment_state(self, assignment_id):
        """Same integrity boundary for a displayed edition alternative or resolved cell."""
        assignment = self.assignments.get(assignment_id)
        if assignment is None:
            return "CHANGED"
        file = assignment.archive_file
        if file.pk not in self._verified:
            self._verified[file.pk] = library_services.verify_file(file)
            self._current_assignments[file.pk] = set(
                archive.ArchiveAssignment.objects.usable()
                .filter(
                    archive_file_id=file.pk,
                    archive_file__revision=file.revision,
                    archive_file__arrangement_id=file.arrangement_id,
                )
                .values_list("pk", "part_id")
            )
        if (assignment.pk, assignment.part_id) not in self._current_assignments[file.pk]:
            return "CHANGED"
        return "VERIFIED" if self._verified[file.pk] else "CORRUPT"

    def ordered_inputs(self, position_id, participant_id):
        """Expose the uniform legacy contract without changing selection or snapshots.

        No proposal is approved here. New content project activation must add
        versioned relational pins before expanding the currently legacy-only
        resolution path. An unavailable explicit/preferred choice never falls back.
        """
        from apps.archive.content_contract import legacy_content_edition

        result = self.verified_resolution(position_id, participant_id)
        if not result.usable:
            return result, None
        edition = legacy_content_edition(result.assignment_id)
        if (
            edition.arrangement_id != self.positions[position_id].arrangement_id
            or edition.part_id != result.effective_part_id
            or any(
                entry.file_id != result.file_id
                or entry.file_revision != result.file_revision
                or entry.source_version_id != result.source_version_id
                or entry.sha256 != result.sha256
                or entry.byte_size != result.byte_size
                or entry.root_kind != result.root_kind
                or entry.relative_path != result.relative_path
                for entry in edition.inputs
            )
        ):
            raise ValidationError("Resolved project inputs changed while adapting the ordered contract.")
        # Reject a concurrent approval/eligibility change after the byte check.
        current = ResolutionSession(
            self.project.pk, position_ids=[position_id], participant_ids=[participant_id]
        ).resolve(position_id, participant_id)
        if current != result:
            raise ValidationError("Project selection changed while adapting the ordered contract.")
        return result, edition


def resolve_cell(project_id, position_id, participant_id):
    session = ResolutionSession(project_id, position_ids=[position_id], participant_ids=[participant_id])
    return session.verified_resolution(position_id, participant_id)
