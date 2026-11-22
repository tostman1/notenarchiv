"""Saved project defaults never follow live master edits; explicit subset/guest APIs."""

import pytest
from django.core.exceptions import ValidationError
from django.test import Client
from django.urls import reverse

from apps.catalog.models import Part
from apps.members.models import Member
from apps.projects import participant_services as s
from apps.projects.services import ProjectConflict, duplicate_project, save_project
from tests.test_projects import values


def revision(project):
    project.refresh_from_db()
    return project.revision


@pytest.fixture
def participants_inputs(project_inputs):
    actor, project, arr, parts, slots, participants, role, edition = project_inputs
    members = [
        participants[0].member,
        Member.objects.create(name="Synthetic same name", regular_part=parts[0]),
        Member.objects.create(name="Synthetic same name", regular_part=parts[1]),
    ]
    return actor, project, parts, participants, members, slots


def test_master_edit_does_not_mutate_saved_defaults_or_overrides(participants_inputs):
    actor, project, parts, participants, members, slots = participants_inputs
    participant = participants[0]
    original_override = participant.overrides.get().edition_id
    member = members[0]
    member.regular_part = parts[1]
    member.name = "Synthetic master rename"
    member.revision += 1
    member.save()
    participant.refresh_from_db()
    assert participant.default_part_id == parts[0].pk and participant.display_name != member.name
    s.change_participant(
        project.pk,
        participant.pk,
        action="refresh",
        actor=actor,
        expected_revision=1,
        expected_member_revision=member.revision,
    )
    participant.refresh_from_db()
    assert participant.default_part_id == parts[1].pk and participant.display_name != member.name
    assert participant.overrides.get().edition_id == original_override
    assert participant.role_id is not None
    assert list(project.positions.filter(active=True).values_list("order", flat=True)) == [1, 2, 3]
    s.change_participant(
        project.pk,
        participant.pk,
        action="refresh",
        actor=actor,
        expected_revision=revision(project),
        expected_member_revision=member.revision,
        refresh_name=True,
    )
    participant.refresh_from_db()
    assert participant.display_name == member.name


def test_subset_all_none_guests_and_reselect_preserve_id_and_default(participants_inputs):
    actor, project, parts, participants, members, _slots = participants_inputs
    scope = [member.pk for member in members]
    s.member_subset(project.pk, [members[1].pk], scope_ids=scope, actor=actor, expected_revision=1)
    selected = project.participants.get(member=members[1])
    assert selected.default_part_id == parts[0].pk and selected.member_revision == members[1].revision
    assert not project.participants.get(pk=participants[0].pk).active
    assert project.participants.get(pk=participants[1].pk).active  # guest independent of member scope
    members[1].regular_part = parts[1]
    members[1].save()
    s.deselect_all(project.pk, actor=actor, expected_revision=revision(project))
    assert not project.participants.filter(active=True).exists()
    s.select_all_members(project.pk, actor=actor, expected_revision=revision(project))
    assert project.participants.filter(active=True, member__isnull=False).count() == 3
    refreshed = project.participants.get(member=members[1])
    assert refreshed.pk == selected.pk and refreshed.default_part_id == parts[0].pk


def test_guest_is_project_local_valid_and_clone_remapped(participants_inputs):
    actor, project, parts, _participants, _members, _slots = participants_inputs
    count = Member.objects.count()
    guest = s.add_guest(project.pk, name="Synthetic guest", part_id=parts[1].pk, actor=actor, expected_revision=1)
    assert guest.member_id is None and guest.guest_id and Member.objects.count() == count
    clone = duplicate_project(project.pk, name="Guest clone", actor=actor, expected_revision=revision(project))
    copied = clone.participants.get(display_name="Synthetic guest", default_part=parts[1])
    assert copied.guest_id != guest.guest_id and copied.pk != guest.pk
    Part.objects.filter(pk=parts[1].pk).update(active=False)
    with pytest.raises(ValidationError):
        s.add_guest(
            project.pk, name="Invalid guest", part_id=parts[1].pk, actor=actor, expected_revision=revision(project)
        )


def test_personal_project_default_override_and_master_remain_separate(participants_inputs):
    actor, project, parts, participants, members, _slots = participants_inputs
    before = participants[0].overrides.get().desired_part_id
    s.change_participant(
        project.pk, participants[0].pk, action="default", part_id=parts[1].pk, actor=actor, expected_revision=1
    )
    participants[0].refresh_from_db()
    members[0].refresh_from_db()
    assert participants[0].default_origin == "MANUAL" and members[0].regular_part_id == parts[0].pk
    assert participants[0].overrides.get().desired_part_id == before


def test_cross_scope_stale_refresh_and_batch_invalid_roll_back(participants_inputs):
    actor, project, parts, participants, members, _slots = participants_inputs
    with pytest.raises(ProjectConflict):
        s.change_participant(
            project.pk,
            participants[0].pk,
            action="refresh",
            actor=actor,
            expected_revision=1,
            expected_member_revision=999,
        )
    other = save_project(values("Foreign"), actor=actor)
    with pytest.raises(ValidationError):
        s.change_participant(other.pk, participants[0].pk, action="remove", actor=actor, expected_revision=1)
    assert revision(other) == 1
    with pytest.raises(ValidationError):
        s.member_subset(project.pk, [members[1].pk], scope_ids=[members[0].pk], actor=actor, expected_revision=1)
    Part.objects.filter(pk=parts[1].pk).update(active=False)
    with pytest.raises(ValidationError):
        s.member_subset(
            project.pk,
            [members[1].pk, members[2].pk],
            scope_ids=[m.pk for m in members],
            actor=actor,
            expected_revision=1,
        )
    assert revision(project) == 1 and project.participants.count() == 2


def test_auth_csrf_filters_signed_page_selection_and_guest_ui(participants_inputs, client):
    actor, project, parts, _participants, members, _slots = participants_inputs
    url = reverse("project_participants", args=[project.pk])
    assert client.get(url).status_code == 302
    client.force_login(actor)
    response = client.get(url, {"instrument": str(parts[1].instrument_id)})
    assert response.context["members"].paginator.count == 1
    token = response.context["scope_token"]
    action = reverse("project_participant_select", args=[project.pk])
    csrf = Client(enforce_csrf_checks=True)
    csrf.force_login(actor)
    assert csrf.post(action, {"action": "all", "expected_revision": 1}).status_code == 403
    assert (
        client.post(
            action, {"action": "subset", "scope": token, "member": [str(members[2].pk)], "expected_revision": 1}
        ).status_code
        == 302
    )
    assert client.post(action, {"action": "subset", "scope": token, "expected_revision": 1}).status_code == 409
    assert (
        client.post(
            reverse("project_guest_add", args=[project.pk]),
            {"name": "UI guest", "part": str(parts[0].pk), "expected_revision": revision(project)},
        ).status_code
        == 302
    )


def test_inactive_member_defaults_preserved_and_deselection_retained(participants_inputs):
    actor, project, _parts, participants, members, _slots = participants_inputs
    members[0].active = False
    members[0].save()
    participant = participants[0]
    s.change_participant(project.pk, participant.pk, action="remove", actor=actor, expected_revision=1)
    assert participant.overrides.count() == 1
    with pytest.raises(ValidationError):
        s.change_participant(
            project.pk, participant.pk, action="reactivate", actor=actor, expected_revision=revision(project)
        )
    with pytest.raises(ValidationError):
        participant.history.first().save()


def test_member_and_project_limits_and_unchanged_other_filtered_participants(participants_inputs, monkeypatch):
    actor, project, parts, participants, members, _slots = participants_inputs
    s.member_subset(project.pk, [members[2].pk], scope_ids=[members[2].pk], actor=actor, expected_revision=1)
    assert project.participants.get(pk=participants[0].pk).active
    monkeypatch.setattr(s, "MAX_PARTICIPANTS", 3)
    with pytest.raises(ValidationError):
        s.add_guest(project.pk, name="Excess", part_id=parts[0].pk, actor=actor, expected_revision=revision(project))


def test_scope_token_actor_invalid_guest_and_archived_defaults(participants_inputs, client):
    actor, project, parts, participants, members, _slots = participants_inputs
    client.force_login(actor)
    response = client.get(reverse("project_participants", args=[project.pk]))
    token = response.context["scope_token"]
    from django.contrib.auth import get_user_model

    other = get_user_model().objects.create_user("synthetic-other-selection")
    client.force_login(other)
    assert (
        client.post(
            reverse("project_participant_select", args=[project.pk]),
            {"action": "subset", "scope": token, "expected_revision": 1, "member": [str(members[1].pk)]},
        ).status_code
        == 409
    )
    assert (
        client.post(
            reverse("project_guest_add", args=[project.pk]), {"name": "Missing part", "expected_revision": 1}
        ).status_code
        == 400
    )
    assert revision(project) == 1
    from apps.projects.services import archive_project

    archive_project(project.pk, actor=actor, expected_revision=1)
    with pytest.raises(ProjectConflict):
        s.change_participant(
            project.pk,
            participants[0].pk,
            action="default",
            part_id=parts[1].pk,
            actor=actor,
            expected_revision=revision(project),
        )


def test_duplicate_selection_empty_scope_and_stale_manual_default(participants_inputs):
    actor, project, parts, participants, members, _slots = participants_inputs
    with pytest.raises(ValidationError):
        s.member_subset(
            project.pk, [members[1].pk, members[1].pk], scope_ids=[members[1].pk], actor=actor, expected_revision=1
        )
    s.member_subset(project.pk, [], scope_ids=[], actor=actor, expected_revision=1)
    assert project.participants.filter(active=True).count() == 2
    with pytest.raises(ProjectConflict):
        s.change_participant(
            project.pk, participants[0].pk, action="default", part_id=parts[1].pk, actor=actor, expected_revision=1
        )


def test_all_then_none_retains_guest_override_and_role(participants_inputs):
    actor, project, _parts, participants, members, _slots = participants_inputs
    ids = set(project.participants.values_list("pk", flat=True))
    s.select_all_members(project.pk, actor=actor, expected_revision=1)
    assert project.participants.filter(active=True).count() == 4
    s.deselect_all(project.pk, actor=actor, expected_revision=revision(project))
    assert ids <= set(project.participants.values_list("pk", flat=True))
    participant = project.participants.get(pk=participants[0].pk)
    assert participant.role_id and participant.overrides.count() == 1
    assert not project.participants.filter(active=True).exists()


def test_limit_all_refuses_truncation_and_manual_guest_default(participants_inputs, monkeypatch):
    actor, project, parts, participants, _members, _slots = participants_inputs
    monkeypatch.setattr(s, "MAX_PARTICIPANTS", 2)
    with pytest.raises(ValidationError):
        s.select_all_members(project.pk, actor=actor, expected_revision=1)
    assert revision(project) == 1
    guest = s.change_participant(
        project.pk, participants[1].pk, action="default", part_id=parts[1].pk, actor=actor, expected_revision=1
    )
    assert guest.default_origin == "MANUAL" and guest.member_id is None


def test_paginated_subset_never_changes_another_page_and_invalid_filters(participants_inputs, client):
    actor, project, parts, _participants, _members, _slots = participants_inputs
    for n in range(27):
        Member.objects.create(name=f"Z synthetic {n:02}", regular_part=parts[0])
    client.force_login(actor)
    url = reverse("project_participants", args=[project.pk])
    response = client.get(url, {"page": 2})
    assert len(response.context["members"]) == 5
    first_id = response.context["members"][0].pk
    token = response.context["scope_token"]
    assert (
        client.post(
            reverse("project_participant_select", args=[project.pk]),
            {"action": "subset", "scope": token, "member": [str(first_id)], "expected_revision": 1},
        ).status_code
        == 302
    )
    assert project.participants.filter(active=True).count() == 3
    assert client.get(url, {"instrument": "bad"}).status_code == 400
