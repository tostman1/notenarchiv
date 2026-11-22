"""Explicit musical roles, compatible variants, exceptions and protected history."""

import uuid

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import Client
from django.urls import reverse

from apps.catalog.models import Arrangement, InstrumentVariant, Part, Work
from apps.projects import ensemble_services as e
from apps.projects import models as m
from apps.projects.services import ProjectConflict, archive_project, duplicate_project, save_project
from tests.test_projects import values


def revision(project):
    project.refresh_from_db()
    return project.revision


@pytest.fixture
def ensemble_inputs(db):
    actor = get_user_model().objects.create_user("synthetic-ensemble")
    project = save_project(values("Synthetic ensemble"), actor=actor)
    variants = [
        InstrumentVariant.objects.create(name=name, transposition=key, clef=clef)
        for name, key, clef in [("Posaune", "C", "BASS"), ("Tenorhorn", "B", "TREBLE")]
    ]
    parts = [[Part.objects.create(instrument=variant, code=str(n)) for n in (1, 2, 3, 4)] for variant in variants]
    roles = [
        e.save_role(
            project.pk, code=str(n), label=f"Synthetic role {n}", actor=actor, expected_revision=revision(project)
        )
        for n in (1, 2, 3, 4)
    ]
    positions = [
        m.ProjectPosition.objects.create(
            project=project,
            order=i,
            arrangement=Arrangement.objects.create(work=Work.objects.create(title=f"Synthetic piece {i}"))
            if i < 3
            else None,
        )
        for i in (1, 2, 3)
    ]
    people = [
        m.ProjectParticipant.objects.create(
            project=project, guest_id=uuid.uuid4(), display_name=f"Synthetic person {n}", default_part=parts[n % 2][0]
        )
        for n in range(7)
    ]
    return actor, project, roles, variants, parts, positions, people


def map_part(inputs, role, variant, part, position=None, mapping=None):
    actor, project, *_ = inputs
    return e.save_mapping(
        project.pk,
        role_id=role.pk,
        instrument_id=variant.pk,
        part_id=part.pk,
        position_id=position.pk if position else None,
        mapping_id=mapping.pk if mapping else None,
        actor=actor,
        expected_revision=revision(project),
    )


def test_four_roles_seven_people_same_role_different_notation(ensemble_inputs):
    actor, project, roles, variants, parts, positions, people = ensemble_inputs
    for person in people:
        e.assign_role(project.pk, person.pk, roles[2].pk, actor=actor, expected_revision=revision(project))
    trombone = map_part(ensemble_inputs, roles[2], variants[0], parts[0][2])
    tenorhorn = map_part(ensemble_inputs, roles[2], variants[1], parts[1][2])
    for person in people:
        person.refresh_from_db()
        choice = e.mapping_choice(project.pk, person.role_id, person.default_part.instrument_id, positions[0].pk)
        assert choice.status == "MAPPED" and choice.origin == "PROJECT"
        assert choice.part.instrument_id == person.default_part.instrument_id
        assert choice.part.pk in {trombone.part_id, tenorhorn.part_id}
        assert person.default_part.code == "1"  # role is not a saved default rewrite
    assert project.roles.count() == 4 and project.participants.count() == 7


def test_position_exception_wins_and_explicit_clear_returns_to_project_mapping(ensemble_inputs):
    _actor, project, roles, variants, parts, positions, _people = ensemble_inputs
    default = map_part(ensemble_inputs, roles[2], variants[0], parts[0][2])
    exception = map_part(ensemble_inputs, roles[2], variants[0], parts[0][1], positions[0])
    choice = e.mapping_choice(project.pk, roles[2].pk, variants[0].pk, positions[0].pk)
    assert choice.part.pk == parts[0][1].pk
    assert choice.origin == "POSITION"
    assert e.mapping_choice(project.pk, roles[2].pk, variants[0].pk, positions[1].pk).mapping.pk == default.pk
    actor = ensemble_inputs[0]
    e.clear_mapping(project.pk, exception.pk, actor=actor, expected_revision=revision(project))
    assert e.mapping_choice(project.pk, roles[2].pk, variants[0].pk, positions[0].pk).origin == "PROJECT"
    assert m.EnsembleMapping.objects.get(pk=exception.pk).active is False
    map_part(ensemble_inputs, roles[2], variants[0], parts[0][3], positions[0], exception)
    assert m.EnsembleMapping.objects.get(pk=exception.pk).active


def test_missing_mapping_and_same_number_never_establish_compatibility(ensemble_inputs):
    actor, project, roles, variants, parts, positions, _people = ensemble_inputs
    assert e.mapping_choice(project.pk, roles[2].pk, variants[0].pk).status == "MISSING"
    with pytest.raises(ValidationError):
        map_part(ensemble_inputs, roles[2], variants[0], parts[1][2])
    with pytest.raises(ValidationError):
        map_part(ensemble_inputs, roles[2], variants[0], parts[0][2], positions[2])
    assert m.EnsembleMapping.objects.count() == 0
    assert e.mapping_choice(project.pk, uuid.uuid4(), variants[0].pk).status == "INVALID_ROLE"
    assert actor.is_active


def test_foreign_role_position_participant_and_scope_retarget_rejected(ensemble_inputs):
    actor, project, roles, variants, parts, positions, people = ensemble_inputs
    other = save_project(values("Other"), actor=actor)
    foreign = m.ProjectRole.objects.create(project=other, code="3")
    for kwargs in [
        dict(role_id=foreign.pk),
        dict(
            position_id=m.ProjectPosition.objects.create(
                project=other, order=1, arrangement=positions[0].arrangement
            ).pk
        ),
    ]:
        data = dict(role_id=roles[2].pk, instrument_id=variants[0].pk, part_id=parts[0][2].pk)
        data.update(kwargs)
        with pytest.raises(ValidationError):
            e.save_mapping(project.pk, actor=actor, expected_revision=revision(project), **data)
    with pytest.raises(ValidationError):
        e.assign_role(other.pk, people[0].pk, foreign.pk, actor=actor, expected_revision=1)
    mapping = map_part(ensemble_inputs, roles[2], variants[0], parts[0][2])
    with pytest.raises(ValidationError):
        map_part(ensemble_inputs, roles[2], variants[0], parts[0][2], positions[0], mapping)


def test_stale_revision_archived_edits_and_referenced_role_retention(ensemble_inputs):
    actor, project, roles, variants, parts, _positions, people = ensemble_inputs
    old = revision(project)
    e.assign_role(project.pk, people[0].pk, roles[2].pk, actor=actor, expected_revision=old)
    with pytest.raises(ProjectConflict):
        e.assign_role(project.pk, people[1].pk, roles[2].pk, actor=actor, expected_revision=old)
    with pytest.raises(ValidationError):
        e.set_role_active(project.pk, roles[2].pk, active=False, actor=actor, expected_revision=revision(project))
    e.assign_role(project.pk, people[0].pk, None, actor=actor, expected_revision=revision(project))
    e.set_role_active(project.pk, roles[2].pk, active=False, actor=actor, expected_revision=revision(project))
    assert e.mapping_choice(project.pk, roles[2].pk, variants[0].pk).status == "INVALID_ROLE"
    archive_project(project.pk, actor=actor, expected_revision=revision(project))
    with pytest.raises(ProjectConflict):
        e.save_role(project.pk, code="5", label="Denied", actor=actor, expected_revision=revision(project))


def test_mapping_history_and_duplicate_keep_protected_parts_and_isolation(ensemble_inputs):
    actor, project, roles, variants, parts, positions, people = ensemble_inputs
    mapping = map_part(ensemble_inputs, roles[2], variants[0], parts[0][2])
    map_part(ensemble_inputs, roles[2], variants[0], parts[0][1], mapping=mapping)
    e.assign_role(project.pk, people[0].pk, roles[2].pk, actor=actor, expected_revision=revision(project))
    clone = duplicate_project(project.pk, name="Clone", actor=actor, expected_revision=revision(project))
    copied = m.EnsembleMapping.objects.get(project=clone)
    assert copied.pk != mapping.pk and copied.role_id != mapping.role_id and copied.part_id == parts[0][1].pk
    assert clone.participants.get(display_name=people[0].display_name).role_id == copied.role_id
    change = project.ensemble_history.filter(event="MAPPING_SAVED", previous_part__isnull=False).get()
    assert change.previous_part_id == parts[0][2].pk
    with pytest.raises(ValidationError):
        change.save()


def test_sqlite_unique_nullable_mapping_scopes_and_inactive_catalog(ensemble_inputs):
    _actor, project, roles, variants, parts, positions, _people = ensemble_inputs
    mapping = map_part(ensemble_inputs, roles[2], variants[0], parts[0][2])
    with pytest.raises(IntegrityError), transaction.atomic():
        m.EnsembleMapping.objects.bulk_create(
            [m.EnsembleMapping(project=project, role=roles[2], instrument=variants[0], part=parts[0][1])]
        )
    Part.objects.filter(pk=parts[0][2].pk).update(active=False)
    assert e.mapping_choice(project.pk, roles[2].pk, variants[0].pk).status == "INVALID_MAPPING"
    assert m.EnsembleMapping.objects.get(pk=mapping.pk).part_id == parts[0][2].pk


def test_auth_csrf_german_ui_invalid_filter_and_conflict(ensemble_inputs, client):
    actor, project, roles, variants, parts, positions, people = ensemble_inputs
    url = reverse("project_ensemble", args=[project.pk])
    assert client.get(url).status_code == 302
    client.force_login(actor)
    assert client.get(url).status_code == 200
    assert client.get(url, {"position": "not-a-uuid"}).status_code == 404
    create = reverse("ensemble_mapping_create", args=[project.pk])
    data = {
        "expected_revision": revision(project),
        "role": str(roles[2].pk),
        "instrument": str(variants[0].pk),
        "part": str(parts[0][2].pk),
    }
    csrf = Client(enforce_csrf_checks=True)
    csrf.force_login(actor)
    assert csrf.post(create, data).status_code == 403
    assert client.post(create, data).status_code == 302
    assert client.post(create, data).status_code == 409
    data["expected_revision"] = revision(project)
    data["part"] = str(parts[1][2].pk)
    assert client.post(create, data).status_code == 400
    assert client.get(reverse("ensemble_role_state", args=[project.pk, roles[2].pk])).status_code == 405


def test_invalid_position_mapping_never_hidden_by_default_and_actor_limit_rollback(ensemble_inputs, monkeypatch):
    actor, project, roles, variants, parts, positions, _people = ensemble_inputs
    map_part(ensemble_inputs, roles[2], variants[0], parts[0][2])
    exception = map_part(ensemble_inputs, roles[2], variants[0], parts[0][1], positions[0])
    Part.objects.filter(pk=exception.part_id).update(active=False)
    result = e.mapping_choice(project.pk, roles[2].pk, variants[0].pk, positions[0].pk)
    assert result.status == "INVALID_MAPPING" and result.origin == "POSITION" and result.part is None
    before = revision(project)
    monkeypatch.setattr(e, "MAX_ROLES", 4)
    with pytest.raises(ValidationError):
        e.save_role(project.pk, code="5", label="Exceeded", actor=actor, expected_revision=before)
    actor.is_active = False
    actor.save()
    with pytest.raises(ValidationError):
        e.clear_mapping(project.pk, exception.pk, actor=actor, expected_revision=before)
    assert revision(project) == before and m.EnsembleMapping.objects.get(pk=exception.pk).active


def test_assign_role_does_not_touch_saved_default_or_personal_override(project_inputs):
    actor, project, _arr, _parts, _slots, people, role, _edition = project_inputs
    before = people[0].default_part_id, people[0].overrides.get().edition_id
    another = e.save_role(project.pk, code="4", label="Synthetic role 4", actor=actor, expected_revision=1)
    e.assign_role(project.pk, people[0].pk, another.pk, actor=actor, expected_revision=revision(project))
    person = project.participants.get(pk=people[0].pk)
    assert (person.default_part_id, person.overrides.get().edition_id) == before
    assert person.role_id == another.pk and role.pk != another.pk


def test_role_edit_normalized_uniqueness_and_reactivate_are_explicit(ensemble_inputs):
    actor, project, roles, _variants, _parts, _positions, _people = ensemble_inputs
    before = revision(project)
    with pytest.raises(ValidationError):
        e.save_role(project.pk, code=" 3 ", label="Duplicate", actor=actor, expected_revision=before)
    assert revision(project) == before
    saved = e.save_role(
        project.pk, role_id=roles[2].pk, code="III", label="Changed role", actor=actor, expected_revision=before
    )
    assert saved.pk == roles[2].pk and saved.code_key == "iii"
    e.set_role_active(project.pk, saved.pk, active=False, actor=actor, expected_revision=revision(project))
    e.set_role_active(project.pk, saved.pk, active=True, actor=actor, expected_revision=revision(project))
    assert project.roles.get(pk=saved.pk).active


def test_mapping_clear_cross_project_and_stale_history_write_roll_back(ensemble_inputs):
    actor, project, roles, variants, parts, _positions, _people = ensemble_inputs
    mapping = map_part(ensemble_inputs, roles[2], variants[0], parts[0][2])
    other = save_project(values("Other mapping project"), actor=actor)
    with pytest.raises(ValidationError):
        e.clear_mapping(other.pk, mapping.pk, actor=actor, expected_revision=1)
    assert revision(other) == 1
    old = revision(project)
    e.clear_mapping(project.pk, mapping.pk, actor=actor, expected_revision=old)
    count = project.ensemble_history.count()
    with pytest.raises(ProjectConflict):
        e.clear_mapping(project.pk, mapping.pk, actor=actor, expected_revision=old)
    assert project.ensemble_history.count() == count


def test_inactive_role_cannot_assign_and_readonly_overview_does_not_mutate(ensemble_inputs, client):
    actor, project, roles, _variants, _parts, _positions, people = ensemble_inputs
    e.set_role_active(project.pk, roles[2].pk, active=False, actor=actor, expected_revision=revision(project))
    before = revision(project), project.ensemble_history.count()
    with pytest.raises(ValidationError):
        e.assign_role(project.pk, people[0].pk, roles[2].pk, actor=actor, expected_revision=before[0])
    client.force_login(actor)
    assert client.get(reverse("project_ensemble", args=[project.pk])).status_code == 200
    assert (revision(project), project.ensemble_history.count()) == before


def test_history_failure_rolls_back_mapping_and_revision(ensemble_inputs, monkeypatch):
    actor, project, roles, variants, parts, _positions, _people = ensemble_inputs
    before = revision(project)

    def fail(*args, **kwargs):
        raise ValidationError("synthetic audit write failure")

    monkeypatch.setattr(e, "_history", fail)
    with pytest.raises(ValidationError):
        map_part(ensemble_inputs, roles[2], variants[0], parts[0][2])
    assert revision(project) == before and not m.EnsembleMapping.objects.exists()
