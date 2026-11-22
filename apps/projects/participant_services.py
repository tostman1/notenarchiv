"""Saved project defaults, explicit refresh and bounded member selection only."""

import uuid

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

from apps.catalog.models import Part
from apps.members.models import Member
from apps.projects import models as m
from apps.projects.services import MAX_PARTICIPANTS, ProjectConflict, edit, reviewer


def playable(identifier):
    part = Part.objects.select_related("instrument").filter(pk=identifier, active=True, instrument__active=True).first()
    if part is None:
        raise ValidationError(_("Wählen Sie eine aktive spielbare Stimme mit eindeutiger Notation."))
    return part


def _state(participant):
    return participant.default_part_id, participant.display_name, participant.active


def _history(project, participant, actor, event, previous=None):
    part, name, active = previous or (None, "", None)
    m.ParticipantChange.objects.create(
        project=project,
        participant=participant,
        actor=reviewer(actor),
        project_revision=project.revision,
        event=event,
        previous_part_id=part,
        selected_part_id=participant.default_part_id,
        previous_name=name,
        selected_name=participant.display_name,
        previous_active=active,
        selected_active=participant.active,
        member_revision=participant.member_revision,
    )


def member_subset(project_id, selected_ids, *, scope_ids, actor, expected_revision):
    """Replace only the explicitly displayed member subset; other people/guests unchanged."""
    if not isinstance(selected_ids, (list, tuple)) or not isinstance(scope_ids, (list, tuple)):
        raise ValidationError(_("Ungültige begrenzte Mitgliedsauswahl."))
    if len(selected_ids) > MAX_PARTICIPANTS or len(scope_ids) > MAX_PARTICIPANTS:
        raise ValidationError(_("Teilnehmergrenze erreicht."))
    try:
        selected = {uuid.UUID(str(value)) for value in selected_ids}
        scope = {uuid.UUID(str(value)) for value in scope_ids}
    except (ValueError, TypeError):
        raise ValidationError(_("Ungültige Mitgliedsauswahl.")) from None
    if len(scope_ids) != len(scope) or len(selected_ids) != len(selected) or not selected <= scope:
        raise ValidationError(_("Mitgliedsauswahl außerhalb der bestätigten Auswahl."))
    with edit(project_id, expected_revision, actor=actor, event="PARTICIPANTS_SELECTED") as project:
        members = {
            member.pk: member
            for member in Member.objects.filter(pk__in=selected, active=True).select_related("regular_part__instrument")
        }
        if set(members) != selected:
            raise ValidationError(_("Gewählte Mitglieder fehlen oder sind inaktiv."))
        for member in members.values():
            playable(member.regular_part_id)
        existing = {row.member_id: row for row in project.participants.filter(member_id__in=scope)}
        active_elsewhere = project.participants.filter(active=True).exclude(member_id__in=scope).count()
        if active_elsewhere + len(selected) > MAX_PARTICIPANTS:
            raise ValidationError(_("Höchstens 500 aktive Teilnehmende pro Projekt."))
        for identifier in scope:
            participant = existing.get(identifier)
            if identifier in selected:
                if participant is None:
                    member = members[identifier]
                    participant = m.ProjectParticipant.objects.create(
                        project=project,
                        member=member,
                        display_name=member.name,
                        default_part=member.regular_part,
                        member_revision=member.revision,
                        default_origin="MEMBER",
                    )
                    _history(project, participant, actor, "MEMBER_ADDED")
                elif not participant.active:
                    playable(participant.default_part_id)
                    previous = _state(participant)
                    participant.active = True
                    participant.save()
                    _history(project, participant, actor, "RESELECTED", previous)
            elif participant and participant.active:
                previous = _state(participant)
                participant.active = False
                participant.save()
                _history(project, participant, actor, "DESELECTED", previous)
        return project


def add_guest(project_id, *, name, part_id, actor, expected_revision):
    with edit(project_id, expected_revision, actor=actor, event="GUEST_ADDED") as project:
        if project.participants.filter(active=True).count() >= MAX_PARTICIPANTS:
            raise ValidationError(_("Höchstens 500 aktive Teilnehmende pro Projekt."))
        participant = m.ProjectParticipant.objects.create(
            project=project,
            guest_id=uuid.uuid4(),
            display_name=name,
            default_part=playable(part_id),
            default_origin="GUEST",
        )
        _history(project, participant, actor, "GUEST_ADDED")
        return participant


def deselect_all(project_id, *, actor, expected_revision):
    with edit(project_id, expected_revision, actor=actor, event="ALL_PARTICIPANTS_DESELECTED") as project:
        if project.participants.filter(active=True).count() > MAX_PARTICIPANTS:
            raise ValidationError(_("Teilnehmergrenze überschritten; Bestand kontrollieren."))
        for participant in project.participants.filter(active=True):
            previous = _state(participant)
            participant.active = False
            participant.save()
            _history(project, participant, actor, "DESELECTED", previous)


def change_participant(
    project_id,
    participant_id,
    *,
    actor,
    expected_revision,
    action,
    part_id=None,
    expected_member_revision=None,
    refresh_name=False,
):
    if action not in {"refresh", "default", "remove", "reactivate"}:
        raise ValidationError(_("Ungültige Teilnehmeraktion."))
    with edit(project_id, expected_revision, actor=actor, event="PARTICIPANT_CHANGED") as project:
        participant = project.participants.select_related("member").filter(pk=participant_id).first()
        if participant is None:
            raise ValidationError(_("Teilnehmende gehören nicht zu diesem Projekt."))
        previous = _state(participant)
        if action == "refresh":
            member = participant.member
            if member is None or not member.active or member.revision != expected_member_revision:
                raise ProjectConflict()
            participant.default_part = playable(member.regular_part_id)
            participant.member_revision = member.revision
            participant.default_origin = "MEMBER"
            if refresh_name:
                participant.display_name = member.name
        elif action == "default":
            participant.default_part = playable(part_id)
            participant.default_origin = "MANUAL"
        elif action == "reactivate":
            if participant.member and not participant.member.active:
                raise ValidationError(_("Inaktives Mitglied kann nicht neu ausgewählt werden."))
            playable(participant.default_part_id)
            if not participant.active and project.participants.filter(active=True).count() >= MAX_PARTICIPANTS:
                raise ValidationError(_("Teilnehmergrenze erreicht."))
            participant.active = True
        else:
            participant.active = False
        participant.save()
        _history(project, participant, actor, action.upper(), previous)
        return participant


def select_all_members(project_id, *, actor, expected_revision):
    # Read only under the same write barrier; bounded all means all regular active
    # members, not a silently truncated page. Guests stay independently selected.
    from django.db import transaction

    with transaction.atomic():
        if type(expected_revision) is not int or expected_revision < 1:
            raise ProjectConflict()
        from django.db.models import F

        if not m.Project.objects.filter(pk=project_id, revision=expected_revision, status="ACTIVE").update(
            revision=F("revision")
        ):
            raise ProjectConflict()
        ids = list(Member.objects.filter(active=True).values_list("pk", flat=True)[: MAX_PARTICIPANTS + 1])
        if len(ids) > MAX_PARTICIPANTS:
            raise ValidationError(_("Zu viele Mitglieder; wählen Sie eine begrenzte Teilmenge."))
        return member_subset(project_id, ids, scope_ids=ids, actor=actor, expected_revision=expected_revision)
