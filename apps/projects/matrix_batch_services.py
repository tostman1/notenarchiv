"""Bounded all-or-nothing same-person exact selections and non-destructive reset."""

import time
from uuid import UUID

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

from apps.archive import edition_services
from apps.projects import matrix_edit_services as manual
from apps.projects import models as m
from apps.projects.services import ProjectConflict, edit, reviewer

MAX_BATCH_CELLS = 25
MAX_BATCH_BYTES = 512 * 1024**2


def position_ids(values):
    if not isinstance(values, (list, tuple)) or not 1 <= len(values) <= MAX_BATCH_CELLS:
        raise ValidationError(_("Eine bis 25 Zellen derselben Person auswählen; nichts geändert."))
    try:
        ids = [UUID(str(value)) for value in values]
    except (ValueError, TypeError, AttributeError):
        raise ValidationError(_("Ungültige Zellenauswahl; nichts geändert.")) from None
    if len(ids) != len(set(ids)):
        raise ValidationError(_("Doppelte Zellenauswahl; nichts geändert."))
    return ids


def scoped_cells(project, participant_id, ids, *, resetting=False):
    person = project.participants.filter(pk=participant_id, active=True).first()
    query = project.positions.filter(pk__in=ids, active=True, arrangement__isnull=False)
    if not resetting:
        query = query.filter(arrangement__active=True, arrangement__work__active=True)
    positions = list(query.order_by("order"))
    if person is None or len(positions) != len(ids):
        raise ValidationError(_("Fremde, entfernte oder Reserve-Zelle ausgewählt; nichts geändert."))
    return person, positions


def set_cells(project_id, participant_id, selections, *, part_id, actor, expected_revision):
    if not isinstance(selections, (list, tuple)):
        raise ValidationError(_("Ungültige Mehrfachauswahl; nichts geändert."))
    if any(not isinstance(item, (list, tuple)) or len(item) != 2 for item in selections):
        raise ValidationError(_("Ungültige Mehrfachauswahl; nichts geändert."))
    ids = position_ids([item[0] for item in selections])
    choices = {}
    cached, checked_files, total_bytes = {}, set(), 0
    deadline = time.monotonic() + 60
    for position_id, (_submitted_id, token) in zip(ids, selections, strict=True):
        try:
            if not isinstance(token, str):
                raise ValidationError("Invalid matrix receipt.")
            if token not in cached:
                cached[token] = manual.selected_choice(token, actor)
            choice = cached[token]
        except ValidationError:
            raise ValidationError(
                _("Mindestens eine konkrete Ausgabe fehlt, ist geändert oder unbestätigt; nichts geändert.")
            ) from None
        if choice.archive_file_id not in checked_files:
            total_bytes += choice.archive_file.byte_size
            checked_files.add(choice.archive_file_id)
        if total_bytes > MAX_BATCH_BYTES or time.monotonic() > deadline:
            raise ValidationError(
                _("Prüfgrenze für Mehrfachänderung überschritten; weniger Zellen auswählen. Nichts geändert.")
            )
        if str(choice.part_id) != str(part_id):
            raise ValidationError(
                _("Alle gewählten Ausgaben müssen genau zur gewählten Stimme und Notation passen; nichts geändert.")
            )
        choices[position_id] = choice
    with edit(project_id, expected_revision, actor=actor, event="MATRIX_BATCH_SAVED") as project:
        person, positions = scoped_cells(project, participant_id, ids)
        # Validate the complete batch before the first mutation. SQLite writer
        # prevents archive/project state changes between this fence and commit.
        for position in positions:
            choice = choices[position.pk]
            if (
                not edition_services.compatible(position.arrangement_id, choice.part_id)
                .filter(
                    pk=choice.pk,
                    archive_file__revision=choice.archive_file.revision,
                    archive_file__sha256=choice.archive_file.sha256,
                )
                .exists()
            ):
                raise ProjectConflict()
        return [
            manual.save_choice(project, position, person, choices[position.pk], actor=actor, event="BATCH_SAVED")
            for position in positions
        ]


def reset_cells(project_id, participant_id, selected_positions, *, actor, expected_revision):
    ids = position_ids(selected_positions)
    with edit(project_id, expected_revision, actor=actor, event="MATRIX_OVERRIDES_RESET") as project:
        person, positions = scoped_cells(project, participant_id, ids, resetting=True)
        records = {
            row.position_id: row
            for row in m.PartOverride.objects.filter(
                project=project, participant=person, position_id__in=ids, active=True
            )
        }
        for position in positions:
            record = records.get(position.pk)
            if record is None:
                continue
            # Historical pins remain protected, even withdrawn/incompatible ones.
            record.active = False
            record.save()
            m.MatrixChange.objects.create(
                project=project,
                project_revision=project.revision,
                actor=reviewer(actor),
                participant=person,
                position=position,
                override=record,
                event="OVERRIDE_RESET",
                previous_part_id=record.desired_part_id,
                previous_edition_id=record.edition_id,
            )
        return len(records)
