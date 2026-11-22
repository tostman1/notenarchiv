"""Explicit project role/mapping edits; no part-number inference or transposition."""

from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from apps.catalog.models import InstrumentVariant, Part, normalized
from apps.projects import models as m
from apps.projects.participant_services import playable
from apps.projects.services import edit, reviewer

MAX_ROLES = 1000
MAX_MAPPINGS = 20_000


def _history(project, actor, event, **values):
    return m.EnsembleChange.objects.create(
        project=project, actor=reviewer(actor), project_revision=project.revision, event=event, **values
    )


def save_role(project_id, *, code, label, actor, expected_revision, role_id=None):
    with edit(project_id, expected_revision, actor=actor, event="ENSEMBLE_ROLE_SAVED") as project:
        if role_id is None:
            if project.roles.count() >= MAX_ROLES:
                raise ValidationError(_("Höchstens 1000 Rollen pro Projekt."))
            role = m.ProjectRole(project=project)
            before = {}
        else:
            role = project.roles.filter(pk=role_id).first()
            if role is None:
                raise ValidationError(_("Rolle gehört nicht zu diesem Projekt."))
            before = {"code": role.code, "label": role.label, "active": role.active}
        if project.roles.filter(code_key=normalized(code)).exclude(pk=role.pk).exists():
            raise ValidationError(_("Dieses Rollenkürzel ist im Projekt bereits vorhanden."))
        role.code, role.label = code, label
        role.save()
        _history(
            project,
            actor,
            "ROLE_SAVED",
            role=role,
            before=before,
            after={"code": role.code, "label": role.label, "active": role.active},
        )
        return role


def set_role_active(project_id, role_id, *, active, actor, expected_revision):
    with edit(project_id, expected_revision, actor=actor, event="ENSEMBLE_ROLE_STATE") as project:
        role = project.roles.filter(pk=role_id).first()
        if role is None or type(active) is not bool:
            raise ValidationError(_("Ungültige Projektrolle."))
        if not active and project.participants.filter(role=role, active=True).exists():
            raise ValidationError(_("Rolle wird von ausgewählten Teilnehmenden verwendet. Zuerst ausdrücklich lösen."))
        before = role.active
        role.active = active
        role.save()
        _history(project, actor, "ROLE_STATE", role=role, before={"active": before}, after={"active": active})
        return role


def assign_role(project_id, participant_id, role_id, *, actor, expected_revision):
    with edit(project_id, expected_revision, actor=actor, event="PARTICIPANT_ROLE_SAVED") as project:
        participant = project.participants.filter(pk=participant_id, active=True).first()
        if participant is None:
            raise ValidationError(_("Wählen Sie eine ausgewählte Person dieses Projekts."))
        role = project.roles.filter(pk=role_id, active=True).first() if role_id is not None else None
        if role_id is not None and role is None:
            raise ValidationError(_("Wählen Sie eine aktive Rolle dieses Projekts."))
        previous = participant.role_id
        participant.role = role
        participant.save()
        _history(
            project, actor, "PARTICIPANT_ROLE", participant=participant, previous_role_id=previous, selected_role=role
        )
        return participant


def save_mapping(
    project_id, *, role_id, instrument_id, part_id, position_id=None, mapping_id=None, actor, expected_revision
):
    with edit(project_id, expected_revision, actor=actor, event="ENSEMBLE_MAPPING_SAVED") as project:
        role = project.roles.filter(pk=role_id, active=True).first()
        instrument = InstrumentVariant.objects.filter(pk=instrument_id, active=True).first()
        part = playable(part_id)
        position = (
            project.positions.filter(
                pk=position_id,
                active=True,
                arrangement__isnull=False,
                arrangement__active=True,
                arrangement__work__active=True,
            ).first()
            if position_id is not None
            else None
        )
        if role is None or instrument is None or part.instrument_id != instrument.pk:
            raise ValidationError(_("Rolle und exakt passende spielbare Instrumentenvariante wählen."))
        if position_id is not None and position is None:
            raise ValidationError(_("Positionsausnahme benötigt ein aktives Stück dieses Projekts, keine Reserve."))
        if mapping_id is None:
            if m.EnsembleMapping.objects.filter(project=project).count() >= MAX_MAPPINGS:
                raise ValidationError(_("Mapping-Grenze erreicht."))
            mapping = m.EnsembleMapping(project=project, role=role, instrument=instrument, position=position)
            previous_part, before = None, {}
        else:
            mapping = m.EnsembleMapping.objects.filter(project=project, pk=mapping_id).first()
            if mapping is None or (mapping.role_id, mapping.instrument_id, mapping.position_id) != (
                role.pk,
                instrument.pk,
                position.pk if position else None,
            ):
                raise ValidationError(_("Mapping-Geltungsbereich ist unveränderlich; neue Zuordnung anlegen."))
            previous_part, before = mapping.part_id, {"active": mapping.active}
        if (
            m.EnsembleMapping.objects.filter(project=project, role=role, instrument=instrument, position=position)
            .exclude(pk=mapping.pk)
            .exists()
        ):
            raise ValidationError(_("Zuordnung für diesen Geltungsbereich existiert bereits; ausdrücklich bearbeiten."))
        mapping.part, mapping.active = part, True
        mapping.save()
        _history(
            project,
            actor,
            "MAPPING_SAVED",
            mapping=mapping,
            role=role,
            previous_part_id=previous_part,
            selected_part=part,
            before=before,
            after={"active": True},
        )
        return mapping


def clear_mapping(project_id, mapping_id, *, actor, expected_revision):
    with edit(project_id, expected_revision, actor=actor, event="ENSEMBLE_MAPPING_CLEARED") as project:
        mapping = m.EnsembleMapping.objects.filter(project=project, pk=mapping_id).first()
        if mapping is None:
            raise ValidationError(_("Mapping gehört nicht zu diesem Projekt."))
        before = mapping.active
        mapping.active = False
        mapping.save()
        _history(
            project,
            actor,
            "MAPPING_CLEARED",
            mapping=mapping,
            role=mapping.role,
            previous_part=mapping.part,
            before={"active": before},
            after={"active": False},
        )
        return mapping


@dataclass(frozen=True)
class MappingChoice:
    status: str
    origin: str
    part: Part | None = None
    mapping: m.EnsembleMapping | None = None


def mapping_choice(project_id, role_id, instrument_id, position_id=None, *, mappings=None, role=None):
    """Only the mapping component, reusable by WP-32; no edition/override algorithm."""
    role = role or m.ProjectRole.objects.filter(project_id=project_id, pk=role_id).first()
    if role is None or role.pk != role_id or role.project_id != project_id or not role.active:
        return MappingChoice("INVALID_ROLE", "NONE")
    if mappings is None:
        mappings = m.EnsembleMapping.objects.filter(
            project_id=project_id, role_id=role_id, instrument_id=instrument_id, active=True
        ).select_related("part__instrument", "position__arrangement__work")
    relevant = [
        item
        for item in mappings
        if item.project_id == project_id
        and item.role_id == role_id
        and item.instrument_id == instrument_id
        and item.active
    ]
    exceptions = [item for item in relevant if item.position_id == position_id and position_id is not None]
    defaults = [item for item in relevant if item.position_id is None]
    selected, origin = (exceptions, "POSITION") if exceptions else (defaults, "PROJECT")
    if not selected:
        return MappingChoice("MISSING", "NONE")
    if len(selected) != 1:
        return MappingChoice("INVALID_MAPPING", origin)
    mapping = selected[0]
    if not mapping.part.active or not mapping.part.instrument.active or mapping.part.instrument_id != instrument_id:
        return MappingChoice("INVALID_MAPPING", origin)
    if mapping.position_id and (not mapping.position.active or not mapping.position.arrangement_id):
        return MappingChoice("INVALID_MAPPING", origin)
    if mapping.position_id and mapping.position.project_id != project_id:
        return MappingChoice("INVALID_MAPPING", origin)
    if mapping.position_id and (
        not mapping.position.arrangement.active or not mapping.position.arrangement.work.active
    ):
        return MappingChoice("INVALID_MAPPING", origin)
    return MappingChoice("MAPPED", origin, mapping.part, mapping)
