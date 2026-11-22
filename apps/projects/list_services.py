"""One shared ordered list, serialized revision edits and stable reserve identities."""

from uuid import UUID

from django.core.exceptions import ValidationError
from django.db.models import F
from django.utils.translation import gettext as _

from apps.catalog.models import Arrangement
from apps.projects import models as m
from apps.projects.services import MAX_POSITIONS, edit, reviewer


def positions(project):
    return (
        m.ProjectPosition.objects.filter(project=project, active=True)
        .select_related("arrangement__work")
        .order_by("order", "pk")
    )


def _ordered(project):
    rows = list(positions(project)[: MAX_POSITIONS + 1])
    if len(rows) > MAX_POSITIONS or [row.order for row in rows] != list(range(1, len(rows) + 1)):
        raise ValidationError(_("Ungültige Stücklistenreihenfolge; bitte kontrollieren."))
    return rows


def _arrangement(identifier):
    if identifier is None:
        return None
    try:
        return Arrangement.objects.get(pk=identifier, active=True, work__active=True)
    except (Arrangement.DoesNotExist, ValidationError, ValueError):
        raise ValidationError(_("Wählen Sie ein aktives Arrangement aus der Bibliothek.")) from None


def _renumber(project, rows):
    # Offset removes every old unique index value before writing dense final order.
    existing = m.ProjectPosition.objects.filter(project=project, active=True)
    maximum = max([row.order or 0 for row in rows] + [MAX_POSITIONS])
    existing.update(order=F("order") + maximum + MAX_POSITIONS + 1)
    for number, row in enumerate(rows, 1):
        row.order = number
    m.ProjectPosition.objects.bulk_update(rows, ["order"])


def _history(project, row, actor, event, *, before_arrangement=None, before_order=None, before_active=None):
    m.PositionChange.objects.create(
        project=project,
        position=row,
        actor=reviewer(actor),
        project_revision=project.revision,
        event=event,
        previous_arrangement_id=before_arrangement,
        selected_arrangement_id=row.arrangement_id,
        previous_order=before_order,
        selected_order=row.order,
        previous_active=before_active,
        selected_active=row.active,
    )


def insert(project_id, *, arrangement_id=None, at=None, actor, expected_revision):
    with edit(project_id, expected_revision, actor=actor, event="POSITION_INSERTED") as project:
        rows = _ordered(project)
        if len(rows) >= MAX_POSITIONS:
            raise ValidationError(_("Höchstens 1000 gemeinsame Positionen möglich."))
        at = len(rows) + 1 if at is None else at
        if type(at) is not int or not 1 <= at <= len(rows) + 1:
            raise ValidationError(_("Ungültige Einfügeposition."))
        row = m.ProjectPosition.objects.create(
            project=project, order=len(rows) + 1, arrangement=_arrangement(arrangement_id)
        )
        rows.insert(at - 1, row)
        _renumber(project, rows)
        _history(project, row, actor, "INSERTED")
        return row


def reorder(project_id, identifiers, *, actor, expected_revision):
    if not isinstance(identifiers, (list, tuple)) or len(identifiers) > MAX_POSITIONS:
        raise ValidationError(_("Ungültige Reihenfolge."))
    try:
        ids = [UUID(str(value)) for value in identifiers]
    except (ValueError, TypeError):
        raise ValidationError(_("Ungültige Positions-ID.")) from None
    with edit(project_id, expected_revision, actor=actor, event="POSITIONS_REORDERED") as project:
        current = _ordered(project)
        by_id = {row.pk: row for row in current}
        if len(ids) != len(by_id) or set(ids) != set(by_id):
            raise ValidationError(_("Reihenfolge muss jede gemeinsame Position genau einmal enthalten."))
        before = {row.pk: row.order for row in current}
        rows = [by_id[value] for value in ids]
        _renumber(project, rows)
        for row in rows:
            if row.order != before[row.pk]:
                _history(
                    project,
                    row,
                    actor,
                    "MOVED",
                    before_arrangement=row.arrangement_id,
                    before_order=before[row.pk],
                    before_active=True,
                )
        return rows


def move(project_id, position_id, at, *, actor, expected_revision):
    # Outer edit obtains the SQLite boundary; shared atomic renumbering follows.
    with edit(project_id, expected_revision, actor=actor, event="POSITION_MOVED") as project:
        rows = _ordered(project)
        if type(at) is not int or not 1 <= at <= len(rows):
            raise ValidationError(_("Ungültige Zielposition."))
        row = next((row for row in rows if str(row.pk) == str(position_id)), None)
        if row is None:
            raise ValidationError(_("Position gehört nicht zur gemeinsamen Stückliste."))
        old_order = row.order
        rows.remove(row)
        rows.insert(at - 1, row)
        _renumber(project, rows)
        _history(
            project,
            row,
            actor,
            "MOVED",
            before_arrangement=row.arrangement_id,
            before_order=old_order,
            before_active=True,
        )
        return row


def replace(project_id, position_id, arrangement_id, *, actor, expected_revision, acknowledge=False):
    with edit(project_id, expected_revision, actor=actor, event="POSITION_REPLACED") as project:
        row = next((row for row in _ordered(project) if str(row.pk) == str(position_id)), None)
        if row is None:
            raise ValidationError(_("Position gehört nicht zur gemeinsamen Stückliste."))
        target = _arrangement(arrangement_id)
        old = row.arrangement_id
        if old is not None and old != (target.pk if target else None) and not acknowledge:
            raise ValidationError(_("Bestätigen Sie den kontrollierten Austausch des Arrangements."))
        row.arrangement = target
        row.save()
        if row.arrangement_id != old:
            row.overrides.update(needs_revalidation=True)
            row.edition_preferences.update(needs_revalidation=True)
        _history(project, row, actor, "REPLACED", before_arrangement=old, before_order=row.order, before_active=True)
        return row


def remove(project_id, position_id, *, actor, expected_revision):
    with edit(project_id, expected_revision, actor=actor, event="POSITION_REMOVED") as project:
        rows = _ordered(project)
        row = next((row for row in rows if str(row.pk) == str(position_id)), None)
        if row is None:
            raise ValidationError(_("Position gehört nicht zur gemeinsamen Stückliste."))
        before = row.order
        rows.remove(row)
        row.active, row.order = False, None
        row.save()
        row.overrides.update(needs_revalidation=True)
        row.edition_preferences.update(needs_revalidation=True)
        _renumber(project, rows)
        _history(
            project,
            row,
            actor,
            "REMOVED",
            before_arrangement=row.arrangement_id,
            before_order=before,
            before_active=True,
        )
        return row
