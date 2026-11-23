"""AS-04/08 atomic same-person exact batch edits and explicit retained-history reset."""

import uuid

import pytest
from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError
from django.test import Client
from django.urls import reverse

from apps.archive import services as review
from apps.projects import matrix_batch_services as batch
from apps.projects import matrix_edit_services as manual
from apps.projects import models as m
from apps.projects import participant_services
from apps.projects import resolution_services as resolver
from apps.projects.services import ProjectConflict, duplicate_project
from tests.test_resolution import resolver_inputs as _fixture

resolver_inputs = _fixture


def selections(inputs, positions=None, file=None):
    actor, _project, _arr, _parts, _people, slots, first, *_ = inputs
    return [
        (slot.pk, manual.choice_token((file or first).assignments.get(), actor)) for slot in (positions or slots[:2])
    ]


def apply(inputs, choices=None, revision=1):
    actor, project, _arr, parts, people, *_ = inputs
    return batch.set_cells(
        project.pk,
        people[2].pk,
        choices or selections(inputs),
        part_id=parts[1].pk,
        actor=actor,
        expected_revision=revision,
    )


def test_batch_part_two_while_three_exists_reset_one_and_reactivate(resolver_inputs):
    actor, project, _arr, parts, people, slots, first, _second, make = resolver_inputs
    make(3, part=parts[2])
    before = list(project.positions.values_list("pk", "order"))
    records = apply(resolver_inputs)
    assert len(records) == 2 and project.matrix_history.count() == 2
    project.refresh_from_db()
    assert project.revision == 2
    assert all(
        resolver.resolve_cell(project.pk, slot.pk, people[2].pk).assignment_id == first.assignments.get().pk
        for slot in slots[:2]
    )
    assert batch.reset_cells(project.pk, people[2].pk, [slots[0].pk], actor=actor, expected_revision=2) == 1
    reset = resolver.resolve_cell(project.pk, slots[0].pk, people[2].pk)
    assert reset.part_origin == "SAVED_DEFAULT" and reset.desired_part_id == parts[2].pk and reset.override_id is None
    assert resolver.resolve_cell(project.pk, slots[1].pk, people[2].pk).part_origin == "PERSONAL"
    records[0].refresh_from_db()
    assert not records[0].active and records[0].edition_id == first.assignments.get().pk
    assert project.matrix_history.get(event="OVERRIDE_RESET").previous_edition_id == first.assignments.get().pk
    updated = manual.set_cell(
        project.pk, slots[0].pk, people[2].pk, selections(resolver_inputs)[0][1], actor=actor, expected_revision=3
    )
    assert updated.pk == records[0].pk and updated.active
    assert not m.PartOverride.objects.filter(participant=people[1]).exists()
    assert list(project.positions.values_list("pk", "order")) == before
    people[2].refresh_from_db()
    assert people[2].default_part_id == parts[2].pk


@pytest.mark.parametrize("bad", ["missing", "duplicate", "reserve", "foreign", "notation", "corrupt", "withdrawn"])
def test_invalid_batch_never_applies_first_cell(resolver_inputs, settings, bad):
    actor, project, _arr, parts, people, slots, first, second, make = resolver_inputs
    choices = selections(resolver_inputs)
    if bad == "missing":
        choices[1] = (slots[1].pk, "")
    elif bad == "duplicate":
        choices[1] = choices[0]
    elif bad == "reserve":
        choices[1] = (slots[2].pk, choices[1][1])
    elif bad == "foreign":
        choices[1] = (uuid.uuid4(), choices[1][1])
    elif bad == "notation":
        choices[1] = (slots[1].pk, manual.choice_token(make(3, part=parts[3]).assignments.get(), actor))
    else:
        choices[1] = (slots[1].pk, manual.choice_token(second.assignments.get(), actor))
        if bad == "withdrawn":
            review.withdraw(second.pk, actor=actor, expected_revision=second.revision)
        else:
            (settings.CURATED_DIR / second.relative_path).write_bytes(b"synthetic corrupt batch")
    with pytest.raises(ValidationError):
        apply(resolver_inputs, choices)
    assert not m.PartOverride.objects.exists() and project.matrix_history.count() == 0
    project.refresh_from_db()
    assert project.revision == 1


def test_post_hash_archive_race_and_mid_audit_failure_roll_back(resolver_inputs, monkeypatch):
    actor, project, _arr, _parts, _people, _slots, first, second, *_ = resolver_inputs
    choices = selections(resolver_inputs)
    choices[1] = (choices[1][0], manual.choice_token(second.assignments.get(), actor))
    verify = manual.library_services.verify_file

    def changed(file):
        result = verify(file)
        if file.pk == second.pk:
            review.withdraw(first.pk, actor=actor, expected_revision=first.revision)
        return result

    with monkeypatch.context() as patch:
        patch.setattr(manual.library_services, "verify_file", changed)
        with pytest.raises(ProjectConflict):
            apply(resolver_inputs, choices)
    assert not m.PartOverride.objects.exists()
    create = m.MatrixChange.objects.create

    def fail_second(**kwargs):
        if m.MatrixChange.objects.count():
            raise ValidationError("synthetic second audit failure")
        return create(**kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(m.MatrixChange.objects, "create", fail_second)
        with pytest.raises(ValidationError):
            apply(resolver_inputs, selections(resolver_inputs, file=second))
    assert not m.PartOverride.objects.exists() and not m.MatrixChange.objects.exists()
    project.refresh_from_db()
    assert project.revision == 1


def test_reset_withdrawn_pin_retains_protection_clone_and_default_overrides(resolver_inputs):
    actor, project, _arr, parts, people, slots, first, *_ = resolver_inputs
    apply(resolver_inputs)
    participant_services.change_participant(
        project.pk, people[2].pk, action="default", part_id=parts[0].pk, actor=actor, expected_revision=2
    )
    assert m.PartOverride.objects.filter(active=True).count() == 2
    review.withdraw(first.pk, actor=actor, expected_revision=first.revision)
    batch.reset_cells(project.pk, people[2].pk, [slots[0].pk], actor=actor, expected_revision=3)
    assert resolver.resolve_cell(project.pk, slots[0].pk, people[2].pk).desired_part_id == parts[0].pk
    assert resolver.resolve_cell(project.pk, slots[1].pk, people[2].pk).status == "INVALID"
    clone = duplicate_project(project.pk, name="Synthetic reset clone", actor=actor, expected_revision=4)
    assert m.PartOverride.objects.filter(project=clone, active=False).count() == 1
    assert not m.MatrixChange.objects.filter(project=clone).exists()
    with pytest.raises(ProtectedError):
        first.assignments.all().delete()


def test_reset_invalid_selection_stale_revision_and_audit_rollback(resolver_inputs, monkeypatch):
    actor, project, _arr, _parts, people, slots, *_ = resolver_inputs
    apply(resolver_inputs)
    for ids in ([slots[0].pk, slots[2].pk], [slots[0].pk, uuid.uuid4()]):
        with pytest.raises(ValidationError):
            batch.reset_cells(project.pk, people[2].pk, ids, actor=actor, expected_revision=2)
    with pytest.raises(ProjectConflict):
        batch.reset_cells(project.pk, people[2].pk, [slots[0].pk], actor=actor, expected_revision=1)

    def failed(**kwargs):
        raise ValidationError("synthetic reset audit failure")

    monkeypatch.setattr(m.MatrixChange.objects, "create", failed)
    with pytest.raises(ValidationError):
        batch.reset_cells(project.pk, people[2].pk, [slot.pk for slot in slots[:2]], actor=actor, expected_revision=2)
    assert m.PartOverride.objects.filter(active=True).count() == 2
    project.refresh_from_db()
    assert project.revision == 2


@pytest.mark.parametrize("ids", [[], [uuid.uuid4()] * 26, ["invalid"], None])
def test_selection_limits_explicit(ids):
    with pytest.raises(ValidationError):
        batch.position_ids(ids)


def test_http_batch_auth_csrf_partial_nojs_reset_errors(resolver_inputs, client):
    actor, project, _arr, parts, people, slots, first, *_ = resolver_inputs
    url = reverse("matrix_batch_edit", args=[project.pk, people[2].pk])
    prefix = f"batch-{people[2].pk}"
    data = {
        prefix + "-action": "save",
        prefix + "-expected_revision": 1,
        prefix + "-part": str(parts[1].pk),
        prefix + "-positions": [str(slot.pk) for slot in slots[:2]],
        **{prefix + "-choice-" + str(pk): token for pk, token in selections(resolver_inputs)},
    }
    assert client.post(url, data).status_code == 302
    client.force_login(actor)
    csrf = Client(enforce_csrf_checks=True)
    csrf.force_login(actor)
    assert csrf.post(url, data).status_code == 403
    response = client.post(url, data, HTTP_HX_REQUEST="true")
    assert response.status_code == 200 and response.context["project"].revision == 2
    assert client.post(url, data, HTTP_HX_REQUEST="true").status_code == 409
    data[prefix + "-action"] = "reset"
    data[prefix + "-expected_revision"] = 2
    data[prefix + "-positions"] = [str(slots[0].pk)]
    data.pop(prefix + "-part")
    assert client.post(url, data).status_code == 302
    assert m.PartOverride.objects.filter(active=True).count() == 1
    data[prefix + "-positions"] = []
    data[prefix + "-expected_revision"] = 3
    response = client.post(url, data, HTTP_HX_REQUEST="true")
    assert response.status_code == 400 and "nichts geändert" in response.content.decode()
    assert client.get(url).status_code == 405


def test_batch_notation_and_foreign_arrangement_fence(resolver_inputs):
    actor, project, arr, parts, people, slots, first, second, make = resolver_inputs
    file = make(3, part=parts[3])
    records = batch.set_cells(
        project.pk,
        people[2].pk,
        selections(resolver_inputs, file=file),
        part_id=parts[3].pk,
        actor=actor,
        expected_revision=1,
    )
    assert all(row.desired_part_id == parts[3].pk for row in records)
    from apps.catalog.models import Arrangement

    other = Arrangement.objects.create(work=arr.work, edition="Synthetic different batch arrangement")
    extra = m.ProjectPosition.objects.create(project=project, order=4, arrangement=other)
    choices = [selections(resolver_inputs)[0], (extra.pk, selections(resolver_inputs)[1][1])]
    with pytest.raises(ProjectConflict):
        apply(resolver_inputs, choices, revision=2)
    assert m.PartOverride.objects.count() == 2
    assert all(row.edition_id == file.assignments.get().pk for row in m.PartOverride.objects.all())


def test_reset_revalidation_and_missing_default_does_not_choose_music(resolver_inputs):
    actor, project, _arr, parts, people, slots, *_ = resolver_inputs
    apply(resolver_inputs)
    m.PartOverride.objects.filter(project=project).update(needs_revalidation=True)
    batch.reset_cells(project.pk, people[2].pk, [slots[0].pk], actor=actor, expected_revision=2)
    result = resolver.resolve_cell(project.pk, slots[0].pk, people[2].pk)
    assert result.status == "MISSING" and result.desired_part_id == parts[2].pk and result.assignment_id is None
    assert resolver.resolve_cell(project.pk, slots[1].pk, people[2].pk).status == "INVALID"


def test_batch_verification_budget_and_identical_receipt_cache(resolver_inputs, monkeypatch):
    actor, project, *_ = resolver_inputs
    with monkeypatch.context() as patch:
        patch.setattr(batch, "MAX_BATCH_BYTES", 1)
        with pytest.raises(ValidationError, match="Prüfgrenze"):
            apply(resolver_inputs)
    assert not m.PartOverride.objects.exists()
    calls = []
    original = manual.selected_choice

    def counted(token, actor):
        calls.append(token)
        return original(token, actor)

    monkeypatch.setattr(manual, "selected_choice", counted)
    token = selections(resolver_inputs)[0][1]
    apply(resolver_inputs, [(slot.pk, token) for slot in resolver_inputs[5][:2]])
    assert len(calls) == 1 and m.PartOverride.objects.count() == 2


def test_multi_reset_and_selected_no_override_are_guarded_noops(resolver_inputs):
    actor, project, _arr, _parts, people, slots, *_ = resolver_inputs
    assert batch.reset_cells(project.pk, people[2].pk, [slots[0].pk], actor=actor, expected_revision=1) == 0
    apply(resolver_inputs, revision=2)
    assert (
        batch.reset_cells(project.pk, people[2].pk, [slot.pk for slot in slots[:2]], actor=actor, expected_revision=3)
        == 2
    )
    assert not m.PartOverride.objects.filter(active=True).exists()
    assert project.matrix_history.filter(event="OVERRIDE_RESET").count() == 2


def test_inactive_arrangement_can_reset_but_never_save(resolver_inputs):
    actor, project, arr, _parts, people, slots, *_ = resolver_inputs
    apply(resolver_inputs)
    arr.active = False
    arr.save()
    with pytest.raises(ValidationError):
        apply(resolver_inputs, revision=2)
    assert batch.reset_cells(project.pk, people[2].pk, [slots[0].pk], actor=actor, expected_revision=2) == 1
    assert m.PartOverride.objects.filter(active=True).count() == 1
    assert resolver.resolve_cell(project.pk, slots[0].pk, people[2].pk).status == "INVALID"
