"""Scoped replacements and exact editions: precedence, overlays, historical pins."""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import Client
from django.urls import reverse

from apps.archive import services as archive
from apps.catalog.models import Arrangement, Part
from apps.projects import models as m
from apps.projects import rule_services as s
from apps.projects.services import ProjectConflict, archive_project, duplicate_project, save_project
from tests.test_projects import values


def revision(project=None):
    if project is None:
        return m.GlobalRuleState.objects.get(pk=1).revision
    project.refresh_from_db()
    return project.revision


@pytest.fixture
def rule_inputs(edition_inputs):
    actor, arrangement, parts, first, second, make = edition_inputs
    m.GlobalRuleState.objects.get_or_create(pk=1)
    project = save_project(values(), actor=actor)
    positions = [
        m.ProjectPosition.objects.create(project=project, order=n, arrangement=arrangement if n < 3 else None)
        for n in (1, 2, 3)
    ]
    same = [parts[0], *[Part.objects.create(instrument=parts[0].instrument, code=str(n)) for n in (1, 3, 4)]]
    return actor, project, arrangement, same, parts[1], positions, first, second, make


def save(inputs, desired, target, *, global_scope=False, position=None, rule=None):
    actor, project, *_ = inputs
    return s.save_replacement(
        project_id=None if global_scope else project.pk,
        position_id=position.pk if position else None,
        desired_part_id=desired.pk,
        replacement_part_id=target.pk,
        rule_id=rule.pk if rule else None,
        actor=actor,
        expected_revision=revision(None if global_scope else project),
    )


def test_global_project_position_precedence_and_explicit_clear(rule_inputs):
    actor, project, _arr, parts, _foreign, positions, *_ = rule_inputs
    global_ = save(rule_inputs, parts[0], parts[1], global_scope=True)
    project_ = save(rule_inputs, parts[0], parts[2])
    position_ = save(rule_inputs, parts[0], parts[3], position=positions[0])
    assert s.replacement_choice(project.pk, positions[0].pk, parts[0].pk).part.pk == parts[3].pk
    assert s.replacement_choice(project.pk, positions[1].pk, parts[0].pk).origin == "PROJECT"
    s.clear_replacement(position_.pk, project_id=project.pk, actor=actor, expected_revision=revision(project))
    assert s.replacement_choice(project.pk, positions[0].pk, parts[0].pk).rule.pk == project_.pk
    s.clear_replacement(project_.pk, project_id=project.pk, actor=actor, expected_revision=revision(project))
    assert s.replacement_choice(project.pk, positions[0].pk, parts[0].pk).rule.pk == global_.pk
    assert m.ReplacementRule.objects.count() == 2


def test_cross_scope_cycles_and_clear_exposing_cycle_are_rejected(rule_inputs):
    actor, project, _arr, parts, _foreign, positions, *_ = rule_inputs
    save(rule_inputs, parts[0], parts[1], global_scope=True)
    with pytest.raises(ValidationError):
        save(rule_inputs, parts[1], parts[0])
    override = save(rule_inputs, parts[0], parts[2])
    save(rule_inputs, parts[1], parts[0])
    before = revision(project)
    with pytest.raises(ValidationError):
        s.clear_replacement(override.pk, project_id=project.pk, actor=actor, expected_revision=before)
    assert revision(project) == before and m.ReplacementRule.objects.get(pk=override.pk).active
    with pytest.raises(ValidationError):
        save(rule_inputs, parts[2], parts[1], position=positions[0])


def test_invalid_foreign_notation_scope_duplicate_and_stale_revision(rule_inputs):
    actor, project, arr, parts, foreign, positions, *_ = rule_inputs
    for desired, target in [(parts[0], parts[0]), (parts[0], foreign)]:
        with pytest.raises(ValidationError):
            save(rule_inputs, desired, target)
    with pytest.raises(ValidationError):
        save(rule_inputs, parts[0], parts[1], position=positions[2])
    other = save_project(values("Other"), actor=actor)
    foreign_position = m.ProjectPosition.objects.create(project=other, order=1, arrangement=arr)
    with pytest.raises(ValidationError):
        save(rule_inputs, parts[0], parts[1], position=foreign_position)
    rule = save(rule_inputs, parts[0], parts[1])
    with pytest.raises(ValidationError):
        save(rule_inputs, parts[0], parts[2])
    with pytest.raises(ProjectConflict):
        s.clear_replacement(rule.pk, project_id=project.pk, actor=actor, expected_revision=1)
    with pytest.raises(IntegrityError), transaction.atomic():
        m.GlobalReplacementRule.objects.bulk_create(
            [m.GlobalReplacementRule(desired_part=parts[0], replacement_part=parts[0])]
        )


def test_one_hop_component_does_not_walk_fallback_chain(rule_inputs):
    _actor, project, _arr, parts, _foreign, positions, *_ = rule_inputs
    save(rule_inputs, parts[0], parts[1])
    save(rule_inputs, parts[1], parts[2])
    result = s.replacement_choice(project.pk, positions[0].pk, parts[0].pk)
    assert result.part.pk == parts[1].pk and result.origin == "PROJECT"
    Part.objects.filter(pk=parts[1].pk).update(active=False)
    assert s.replacement_choice(project.pk, positions[0].pk, parts[0].pk).status == "INVALID"


def test_project_position_edition_precedence_change_and_clear_keep_history(rule_inputs):
    actor, project, arr, parts, _foreign, positions, first, second, _make = rule_inputs
    pref = s.set_edition(
        project.pk,
        arrangement_id=arr.pk,
        part_id=parts[0].pk,
        edition_id=first.assignments.get().pk,
        actor=actor,
        expected_revision=1,
    )
    pos = s.set_edition(
        project.pk,
        arrangement_id=arr.pk,
        part_id=parts[0].pk,
        edition_id=second.assignments.get().pk,
        position_id=positions[0].pk,
        actor=actor,
        expected_revision=revision(project),
    )
    selected, origin = s.edition_preference(project.pk, positions[0].pk, arr.pk, parts[0].pk)
    assert origin == "POSITION" and selected.pk == pos.pk
    s.clear_edition(project.pk, pos.pk, position_scope=True, actor=actor, expected_revision=revision(project))
    assert s.edition_preference(project.pk, positions[0].pk, arr.pk, parts[0].pk)[0].pk == pref.pk
    updated = s.set_edition(
        project.pk,
        arrangement_id=arr.pk,
        part_id=parts[0].pk,
        edition_id=second.assignments.get().pk,
        actor=actor,
        expected_revision=revision(project),
    )
    assert updated.pk == pref.pk
    assert project.rule_history.filter(previous_edition=first.assignments.get()).exists()
    clone = duplicate_project(project.pk, name="Rule clone", actor=actor, expected_revision=revision(project))
    assert m.ProjectEditionPreference.objects.get(project=clone).edition_id == second.assignments.get().pk


def test_incompatible_pending_withdrawn_corrupt_edition_or_wrong_position_denied(rule_inputs, settings):
    actor, project, arr, parts, foreign, positions, first, second, make = rule_inputs
    for file in (make(3, part=foreign), make(4, confirmed=False)):
        chosen = file.assignments.first()
        with pytest.raises(ValidationError):
            s.set_edition(
                project.pk,
                arrangement_id=arr.pk,
                part_id=parts[0].pk,
                edition_id=chosen.pk if chosen else file.pk,
                actor=actor,
                expected_revision=1,
            )
    archive.withdraw(first.pk, actor=actor, expected_revision=first.revision)
    with pytest.raises(ValidationError):
        s.set_edition(
            project.pk,
            arrangement_id=arr.pk,
            part_id=parts[0].pk,
            edition_id=first.assignments.get().pk,
            actor=actor,
            expected_revision=1,
        )
    (settings.CURATED_DIR / second.relative_path).write_bytes(b"synthetic corrupt copy")
    with pytest.raises(ValidationError):
        s.set_edition(
            project.pk,
            arrangement_id=arr.pk,
            part_id=parts[0].pk,
            edition_id=second.assignments.get().pk,
            actor=actor,
            expected_revision=1,
        )
    assert revision(project) == 1 and not m.ProjectEditionPreference.objects.exists()


def test_replacement_edit_preserves_protected_historical_target_and_no_master_change(rule_inputs):
    actor, project, _arr, parts, _foreign, _positions, *_ = rule_inputs
    rule = save(rule_inputs, parts[0], parts[1])
    updated = save(rule_inputs, parts[0], parts[2], rule=rule)
    assert updated.pk == rule.pk and project.rule_history.filter(previous_part=parts[1]).exists()
    with pytest.raises(ValidationError):
        project.rule_history.first().save()
    archive_project(project.pk, actor=actor, expected_revision=revision(project))
    with pytest.raises(ProjectConflict):
        save(rule_inputs, parts[0], parts[3], rule=rule)


def test_authenticated_rules_ui_csrf_controlled_editions_and_scope(rule_inputs, client):
    actor, project, arr, parts, foreign, positions, first, *_ = rule_inputs
    url = reverse("project_rules", args=[project.pk])
    assert client.get(url).status_code == 302
    client.force_login(actor)
    assert client.get(reverse("global_replacement_rules")).status_code == 200
    csrf = Client(enforce_csrf_checks=True)
    csrf.force_login(actor)
    data = {"expected_revision": 1, "desired_part": str(parts[0].pk), "replacement_part": str(parts[1].pk)}
    create = reverse("project_replacement_create", args=[project.pk])
    assert csrf.post(create, data).status_code == 403
    assert client.post(create, data).status_code == 302
    assert client.post(create, data).status_code == 409
    edition = reverse("project_edition_edit", args=[project.pk])
    response = client.post(
        edition,
        {
            "expected_revision": revision(project),
            "arrangement": str(arr.pk),
            "part": str(foreign.pk),
            "edition": str(first.assignments.get().pk),
        },
    )
    assert response.status_code == 400


def test_invalid_explicit_preference_is_retained_until_deliberate_clear(rule_inputs, client):
    actor, project, arr, parts, _foreign, positions, first, second, _make = rule_inputs
    pref = s.set_edition(
        project.pk,
        arrangement_id=arr.pk,
        part_id=parts[0].pk,
        edition_id=first.assignments.get().pk,
        actor=actor,
        expected_revision=1,
    )
    archive.withdraw(first.pk, actor=actor, expected_revision=first.revision)
    selected, origin = s.edition_preference(project.pk, positions[0].pk, arr.pk, parts[0].pk)
    assert origin == "PROJECT" and selected.edition_id == first.assignments.get().pk
    client.force_login(actor)
    response = client.get(reverse("project_rules", args=[project.pk]))
    assert "Gewählte Ausgabe zurückgezogen, fehlend oder beschädigt" in response.content.decode()
    s.clear_edition(project.pk, pref.pk, actor=actor, expected_revision=revision(project))
    assert s.edition_preference(project.pk, positions[0].pk, arr.pk, parts[0].pk) == (None, "NONE")
    assert m.ProjectEditionPreference.objects.get(pk=pref.pk).edition_id == first.assignments.get().pk


def test_global_rule_change_rejects_cycle_in_existing_project_overlay(rule_inputs):
    _actor, project, _arr, parts, _foreign, _positions, *_ = rule_inputs
    save(rule_inputs, parts[1], parts[0])
    before = revision()
    with pytest.raises(ValidationError):
        save(rule_inputs, parts[0], parts[1], global_scope=True)
    assert revision() == before and not m.GlobalReplacementRule.objects.exists()


def test_edition_hash_check_race_and_wrong_position_roll_back(rule_inputs, monkeypatch):
    actor, project, arr, parts, _foreign, positions, first, _second, _make = rule_inputs
    other_arr = Arrangement.objects.create(work=arr.work, edition="Other arrangement")
    position = m.ProjectPosition.objects.create(project=project, order=4, arrangement=other_arr)
    with pytest.raises(ValidationError):
        s.set_edition(
            project.pk,
            arrangement_id=arr.pk,
            part_id=parts[0].pk,
            edition_id=first.assignments.get().pk,
            position_id=position.pk,
            actor=actor,
            expected_revision=1,
        )
    original = s.edition_services.resolve

    def withdraw(*args, **kwargs):
        result = original(*args, **kwargs)
        archive.withdraw(first.pk, actor=actor, expected_revision=first.revision)
        return result

    monkeypatch.setattr(s.edition_services, "resolve", withdraw)
    with pytest.raises(ProjectConflict):
        s.set_edition(
            project.pk,
            arrangement_id=arr.pk,
            part_id=parts[0].pk,
            edition_id=first.assignments.get().pk,
            actor=actor,
            expected_revision=1,
        )
    assert revision(project) == 1 and not m.ProjectEditionPreference.objects.exists()


def test_foreign_global_scope_history_and_invalid_actor(rule_inputs):
    actor, project, _arr, parts, _foreign, positions, *_ = rule_inputs
    with pytest.raises(ValidationError):
        save(rule_inputs, parts[0], parts[1], global_scope=True, position=positions[0])
    global_ = save(rule_inputs, parts[0], parts[1], global_scope=True)
    with pytest.raises(ValidationError):
        s.clear_replacement(global_.pk, project_id=project.pk, actor=actor, expected_revision=1)
    actor.is_active = False
    actor.save()
    before = revision()
    with pytest.raises(ValidationError):
        s.clear_replacement(global_.pk, actor=actor, expected_revision=before)
    assert revision() == before and m.GlobalReplacementRule.objects.get().active


def test_rule_history_failure_rolls_back_entire_global_update(rule_inputs, monkeypatch):
    actor, _project, _arr, parts, *_ = rule_inputs
    before = revision()

    def fail(*args, **kwargs):
        raise ValidationError("synthetic audit failure")

    monkeypatch.setattr(m.RuleChange.objects, "create", fail)
    with pytest.raises(ValidationError):
        save(rule_inputs, parts[0], parts[1], global_scope=True)
    assert revision() == before and not m.GlobalReplacementRule.objects.exists()


def test_inactive_explicit_rule_never_guesses_compatible_number(rule_inputs):
    actor, project, _arr, parts, foreign, positions, *_ = rule_inputs
    global_ = save(rule_inputs, parts[0], parts[1], global_scope=True)
    local = save(rule_inputs, parts[0], parts[2])
    Part.objects.filter(pk=parts[2].pk).update(active=False)
    choice = s.replacement_choice(project.pk, positions[0].pk, parts[0].pk)
    assert choice.status == "INVALID" and choice.origin == "PROJECT" and choice.part is None
    assert global_.replacement_part_id != foreign.pk
    s.clear_replacement(local.pk, project_id=project.pk, actor=actor, expected_revision=revision(project))
    assert s.replacement_choice(project.pk, positions[0].pk, parts[0].pk).origin == "GLOBAL"
