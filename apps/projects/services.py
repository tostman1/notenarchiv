"""Short write-first SQLite project transactions and isolated graph duplication."""

import uuid
from contextlib import contextmanager

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.projects import models as m

MAX_POSITIONS = 1000
MAX_PARTICIPANTS = 500


class ProjectConflict(ValidationError):
    def __init__(self):
        super().__init__(_("Das Projekt wurde inzwischen geändert. Bitte neu laden und erneut speichern."))


def reviewer(actor):
    identifier = actor.pk if hasattr(actor, "pk") else actor
    actor = get_user_model().objects.filter(pk=identifier, is_active=True).first()
    if actor is None:
        raise ValidationError(_("Eine aktive Anmeldung ist erforderlich."))
    return actor


def record_revision(project, actor, event, data=None):
    return m.ProjectRevision.objects.create(
        project=project,
        actor=actor,
        revision=project.revision,
        event=event,
        data=data or {field: getattr(project, field) for field in FIELDS},
    )


@contextmanager
def edit(project_id, expected_revision, *, actor, event, allow_archived=False):
    with transaction.atomic():
        if type(expected_revision) is not int or expected_revision < 1:
            raise ProjectConflict()
        query = m.Project.objects.filter(pk=project_id, revision=expected_revision)
        if not allow_archived:
            query = query.filter(status="ACTIVE")
        if not query.update(revision=F("revision") + 1, updated_at=timezone.now()):
            raise ProjectConflict()
        project = m.Project.objects.get(pk=project_id)
        actor = reviewer(actor)
        yield project
        record_revision(project, actor, event)


FIELDS = ("name", "layout", "width_mm", "height_mm", "cover_enabled", "cover_title")


def save_project(values, *, actor, project_id=None, expected_revision=0):
    if set(values) != set(FIELDS):
        raise ValidationError(_("Ungültige Projekteinstellungen."))
    if project_id is None:
        if expected_revision != 0:
            raise ProjectConflict()
        with transaction.atomic():
            project = m.Project.objects.create(**values)
            record_revision(project, reviewer(actor), "CREATED")
            return project
    with edit(project_id, expected_revision, actor=actor, event="SETTINGS_CHANGED") as project:
        for key, value in values.items():
            setattr(project, key, value)
        project.save()
        return project


def archive_project(project_id, *, actor, expected_revision, archived=True):
    with edit(
        project_id, expected_revision, actor=actor, event="ARCHIVED" if archived else "REACTIVATED", allow_archived=True
    ) as project:
        project.status = "ARCHIVED" if archived else "ACTIVE"
        project.save()
        return project


def graph_rows(project):
    definitions = (
        (m.ProjectRole, 1000),
        (m.ProjectPosition, MAX_POSITIONS * 2),
        (m.ProjectParticipant, MAX_PARTICIPANTS * 2),
        (m.PartOverride, 50_000),
        (m.ProjectEditionPreference, 10_000),
        (m.PositionEditionPreference, 20_000),
        (m.EnsembleMapping, 20_000),
        (m.ReplacementRule, 2000),
    )
    rows = {}
    for model, limit in definitions:
        related = [field.name for field in model._meta.fields if field.is_relation]
        selected = list(model.objects.filter(project=project).select_related(*related)[: limit + 1])
        if len(selected) > limit:
            raise ValidationError(_("Projekt zu groß für eine begrenzte sichere Duplikation."))
        rows[model] = selected
    return rows


def duplicate_project(project_id, *, name, actor, expected_revision):
    # A no-op conditional UPDATE obtains the SQLite writer boundary without
    # changing the source revision or marking it stale merely for duplication.
    with transaction.atomic():
        if type(expected_revision) is not int or expected_revision < 1:
            raise ProjectConflict()
        if not m.Project.objects.filter(pk=project_id, revision=expected_revision).update(revision=F("revision")):
            raise ProjectConflict()
        actor = reviewer(actor)
        source = m.Project.objects.get(pk=project_id)
        rows = graph_rows(source)
        # Validate source cross-project structure before bulk remapping. Historical
        # withdrawn editions are retained, not asserted usable on duplication.
        for _model, records in rows.items():
            for row in records:
                if isinstance(row, m.Scoped):
                    for field in ("position", "participant", "role"):
                        if getattr(row, field + "_id", None) and getattr(row, field).project_id != source.pk:
                            raise ValidationError("Cross-project reference in source graph.")
                if isinstance(row, (m.PartOverride, m.PositionEditionPreference)) and not row.needs_revalidation:
                    edition = row.edition
                    part_id = row.desired_part_id if isinstance(row, m.PartOverride) else row.part_id
                    if edition and (
                        edition.part_id != part_id or edition.archive_file.arrangement_id != row.position.arrangement_id
                    ):
                        raise ValidationError("Invalid edition reference in project graph.")
                if isinstance(row, m.ProjectEditionPreference) and (
                    row.edition.part_id != row.part_id or row.edition.archive_file.arrangement_id != row.arrangement_id
                ):
                    raise ValidationError("Invalid project edition scope.")
                if isinstance(row, m.EnsembleMapping) and row.part.instrument_id != row.instrument_id:
                    raise ValidationError("Invalid playable variant mapping.")
        values = {field: getattr(source, field) for field in FIELDS}
        values["name"] = name
        clone = m.Project.objects.create(**values, duplicated_from=source)
        maps = {m.Project: {source.pk: clone.pk}}
        for model, records in rows.items():
            maps[model] = {row.pk: uuid.uuid4() for row in records}
        for model, records in rows.items():
            copied = []
            for row in records:
                data = {}
                for field in model._meta.concrete_fields:
                    if field.name in {"id", "created_at"}:
                        continue
                    value = getattr(row, field.attname)
                    if field.is_relation and field.related_model in maps and value is not None:
                        if value not in maps[field.related_model]:
                            raise ValidationError("Cross-project reference in source graph.")
                        value = maps[field.related_model][value]
                    data[field.attname] = value
                if model is m.ProjectParticipant and data["guest_id"]:
                    data["guest_id"] = uuid.uuid4()
                copied.append(model(id=maps[model][row.pk], **data))
            # Existing pinned references may already be withdrawn; retain them
            # unchanged, not reinterpret them as fresh available edition choices.
            # SQL constraints plus complete mapping preserve the source graph.
            model.objects.bulk_create(copied)
        record_revision(clone, actor, "DUPLICATED", {"source": str(source.pk), "source_revision": source.revision})
        return clone


def save_associated(record, *, actor, expected_revision):
    """Validated internal API for WP-29 graph and subsequent package editors."""
    if not isinstance(record, m.Scoped):
        raise ValidationError("Unsupported project record.")
    creating = record._state.adding
    if isinstance(record, m.ProjectPosition):
        raise ValidationError("Shared position changes require the list service and history.")
    if isinstance(record, m.ProjectParticipant):
        raise ValidationError("Participant changes require saved-default selection services and history.")
    if isinstance(record, (m.ProjectRole, m.EnsembleMapping)):
        raise ValidationError("Ensemble edits require the scoped ensemble service and history.")
    if isinstance(record, (m.ReplacementRule, m.ProjectEditionPreference, m.PositionEditionPreference)):
        raise ValidationError("Rule changes require the scoped rule service and history.")
    if creating and getattr(record, "needs_revalidation", False):
        raise ValidationError("New overrides cannot bypass compatibility through revalidation markers.")
    edition_revision = None
    if getattr(record, "edition_id", None):
        from apps.archive import edition_services

        part_id = record.desired_part_id if isinstance(record, m.PartOverride) else record.part_id
        arrangement_id = (
            record.arrangement_id if isinstance(record, m.ProjectEditionPreference) else record.position.arrangement_id
        )
        if (
            edition_services.resolve(arrangement_id, part_id, explicit_assignment_id=record.edition_id).status
            != "AVAILABLE"
        ):
            raise ValidationError("New explicit project choice requires exact confirmed verified bytes.")
        edition_revision = record.edition.archive_file.revision
    with edit(record.project_id, expected_revision, actor=actor, event="ASSOCIATED_CHANGED"):
        if edition_revision is not None:
            from apps.archive.models import ArchiveAssignment

            if (
                not ArchiveAssignment.objects.usable()
                .filter(pk=record.edition_id, archive_file__revision=edition_revision)
                .exists()
            ):
                raise ProjectConflict()
        if not creating:
            previous = type(record).objects.get(pk=record.pk)
            if previous.project_id != record.project_id:
                raise ValidationError("Project scope is immutable.")
        for field in record._meta.concrete_fields:
            if field.is_relation and field.related_model._meta.app_label in {"catalog", "members"}:
                value = getattr(record, field.name)
                if value is not None:
                    value.refresh_from_db()
                    if hasattr(value, "active") and not value.active:
                        raise ValidationError("New project assignments require active catalog/member references.")
                    if hasattr(value, "instrument_id") and not value.instrument.active:
                        raise ValidationError("Playable variant is inactive.")
        if (
            isinstance(record, m.ProjectPosition)
            and creating
            and record.project.positions.filter(active=True).count() >= MAX_POSITIONS
        ):
            raise ValidationError("Project position limit exceeded.")
        if (
            isinstance(record, m.ProjectParticipant)
            and creating
            and record.project.participants.filter(active=True).count() >= MAX_PARTICIPANTS
        ):
            raise ValidationError("Project participant limit exceeded.")
        record.full_clean()
        record.save()
        return record
