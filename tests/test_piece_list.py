"""Shared list acceptance: exact reserve slots, repetition, atomic edits/history."""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import Client
from django.urls import reverse

from apps.catalog.models import Arrangement
from apps.projects import list_services as s
from apps.projects import models as m
from apps.projects.services import ProjectConflict, duplicate_project


def revision(project):
    project.refresh_from_db()
    return project.revision


def test_move_three_to_one_reserve_consumes_number_and_repeated_ids(project_inputs):
    actor, project, arrangement, _parts, rows, *_ = project_inputs
    result = s.move(project.pk, rows[2].pk, 1, actor=actor, expected_revision=1)
    current = list(s.positions(project))
    assert [row.pk for row in current] == [rows[2].pk, rows[0].pk, rows[1].pk]
    assert [row.order for row in current] == [1, 2, 3] and current[2].arrangement_id is None
    assert result.pk == rows[2].pk
    repeated = s.insert(
        project.pk, arrangement_id=arrangement.pk, at=2, actor=actor, expected_revision=revision(project)
    )
    assert repeated.pk not in {row.pk for row in rows} and repeated.arrangement_id == arrangement.pk
    assert list(s.positions(project).values_list("order", flat=True)) == [1, 2, 3, 4]


def test_reserve_fill_replace_keep_slot_and_require_acknowledgement(project_inputs):
    actor, project, arrangement, _parts, rows, *_ = project_inputs
    filled = s.replace(project.pk, rows[1].pk, arrangement.pk, actor=actor, expected_revision=1)
    assert filled.pk == rows[1].pk and filled.order == 2
    other = Arrangement.objects.create(work=arrangement.work, edition="Synthetic replacement")
    with pytest.raises(ValidationError):
        s.replace(project.pk, rows[0].pk, other.pk, actor=actor, expected_revision=revision(project))
    old_revision = revision(project)
    replaced = s.replace(
        project.pk, rows[0].pk, other.pk, actor=actor, expected_revision=old_revision, acknowledge=True
    )
    assert replaced.pk == rows[0].pk and replaced.order == 1
    assert replaced.overrides.get().needs_revalidation and replaced.edition_preferences.get().needs_revalidation
    assert replaced.overrides.get().edition_id is not None  # protected exact historical choice retained
    assert (
        m.PositionChange.objects.get(event="REPLACED", previous_arrangement=arrangement).selected_arrangement_id
        == other.pk
    )


def test_remove_preserves_historical_identity_and_reorders_all(project_inputs):
    actor, project, _arr, _parts, rows, *_ = project_inputs
    removed = s.remove(project.pk, rows[0].pk, actor=actor, expected_revision=1)
    assert removed.pk == rows[0].pk and not removed.active and removed.order is None
    assert removed.overrides.get().needs_revalidation
    assert list(s.positions(project).values_list("order", flat=True)) == [1, 2]
    assert s.positions(project).first().arrangement_id is None
    clone = duplicate_project(project.pk, name="Shared clone", actor=actor, expected_revision=revision(project))
    assert clone.positions.filter(active=False).count() == 1
    assert clone.positions.filter(active=True).count() == 2


@pytest.mark.parametrize("invalid", ["duplicate", "missing", "foreign"])
def test_reorder_validates_entire_set_and_rolls_back(project_inputs, invalid):
    actor, project, _arr, _parts, rows, *_ = project_inputs
    ids = [row.pk for row in rows]
    if invalid == "duplicate":
        ids[2] = ids[0]
    elif invalid == "missing":
        ids.pop()
    else:
        from apps.projects.services import save_project
        from tests.test_projects import values

        other = save_project(values("Foreign"), actor=actor)
        ids[0] = m.ProjectPosition.objects.create(project=other, order=1).pk
    with pytest.raises(ValidationError):
        s.reorder(project.pk, ids, actor=actor, expected_revision=1)
    assert revision(project) == 1 and list(s.positions(project).values_list("pk", flat=True)) == [
        row.pk for row in rows
    ]


def test_atomic_reorder_and_stale_conflict_and_archive_denial(project_inputs):
    actor, project, _arr, _parts, rows, *_ = project_inputs
    s.reorder(project.pk, [row.pk for row in reversed(rows)], actor=actor, expected_revision=1)
    with pytest.raises(ProjectConflict):
        s.remove(project.pk, rows[0].pk, actor=actor, expected_revision=1)
    from apps.projects.services import archive_project

    archive_project(project.pk, actor=actor, expected_revision=revision(project))
    with pytest.raises(ProjectConflict):
        s.insert(project.pk, actor=actor, expected_revision=revision(project))


def test_reserve_insert_active_catalog_and_unique_constraint(project_inputs):
    actor, project, arr, *_ = project_inputs
    reserve = s.insert(project.pk, at=1, actor=actor, expected_revision=1)
    assert reserve.arrangement_id is None and reserve.order == 1
    Arrangement.objects.filter(pk=arr.pk).update(active=False)
    with pytest.raises(ValidationError):
        s.insert(project.pk, arrangement_id=arr.pk, actor=actor, expected_revision=revision(project))
    with pytest.raises(IntegrityError), transaction.atomic():
        m.ProjectPosition.objects.bulk_create([m.ProjectPosition(project=project, order=1)])


def test_ui_auth_csrf_live_library_contents_and_no_personal_list(project_inputs, client):
    actor, project, arr, _parts, rows, *_ = project_inputs
    url = reverse("project_piece_list", args=[project.pk])
    assert client.get(url).status_code == 302
    client.force_login(actor)
    response = client.get(url)
    assert "Alle Teilnehmenden verwenden dieselbe Liste" in response.content.decode()
    assert len(response.context["positions"]) == 3
    search = client.get(reverse("project_library_selection", args=[project.pk]), {"q": "editions"})
    assert search.context["page"].paginator.count >= 1
    action = reverse("project_piece_change", args=[project.pk])
    csrf = Client(enforce_csrf_checks=True)
    csrf.force_login(actor)
    assert csrf.post(action, {"action": "reserve", "expected_revision": 1}).status_code == 403
    assert client.post(action, {"action": "reserve", "expected_revision": 1}).status_code == 302
    assert (
        client.post(action, {"action": "remove", "position": str(rows[0].pk), "expected_revision": 1}).status_code
        == 409
    )
    assert not any(field.name in {"member", "participant"} for field in m.ProjectPosition._meta.fields)


def test_history_references_old_arrangements_and_replace_to_reserve(project_inputs):
    actor, project, arr, _parts, rows, *_ = project_inputs
    row = s.replace(project.pk, rows[0].pk, None, actor=actor, expected_revision=1, acknowledge=True)
    assert row.pk == rows[0].pk and row.order == 1 and row.arrangement_id is None
    change = row.history.get()
    assert change.previous_arrangement_id == arr.pk and change.selected_arrangement_id is None
    with pytest.raises(ValidationError):
        change.save()


def test_failure_mid_reorder_rolls_back_every_number_and_revision(project_inputs, monkeypatch):
    actor, project, _arr, _parts, rows, *_ = project_inputs
    original = m.ProjectPosition.objects.bulk_update

    def fail(*args, **kwargs):
        original(*args, **kwargs)
        raise ValidationError("synthetic failed final order")

    monkeypatch.setattr(m.ProjectPosition.objects, "bulk_update", fail)
    with pytest.raises(ValidationError):
        s.reorder(project.pk, [row.pk for row in reversed(rows)], actor=actor, expected_revision=1)
    assert revision(project) == 1
    assert list(s.positions(project).values_list("order", flat=True)) == [1, 2, 3]
    assert not m.PositionChange.objects.exists()


def test_shared_numbering_not_mutated_by_participant_override_and_limits(project_inputs, monkeypatch):
    actor, project, _arr, parts, rows, participants, *_ = project_inputs
    before = list(s.positions(project).values_list("pk", "order"))
    from apps.projects.services import save_associated

    record = m.PartOverride(project=project, position=rows[2], participant=participants[1], desired_part=parts[0])
    save_associated(record, actor=actor, expected_revision=1)
    assert list(s.positions(project).values_list("pk", "order")) == before
    monkeypatch.setattr(s, "MAX_POSITIONS", 3)
    with pytest.raises(ValidationError):
        s.insert(project.pk, actor=actor, expected_revision=revision(project))


def test_personal_list_parameter_and_invalid_actions_are_rejected(project_inputs, client):
    actor, project, _arr, _parts, rows, participants, *_ = project_inputs
    client.force_login(actor)
    url = reverse("project_piece_change", args=[project.pk])
    assert (
        client.post(
            url,
            {
                "action": "remove",
                "expected_revision": 1,
                "position": str(rows[0].pk),
                "participant": str(participants[0].pk),
            },
        ).status_code
        == 400
    )
    assert client.post(url, {"action": "skip", "expected_revision": 1}).status_code == 400
    assert revision(project) == 1 and project.positions.filter(active=True).count() == 3


def test_empty_list_reserve_then_remove_and_invalid_insertion(project_inputs):
    actor, _project, _arr, *_ = project_inputs
    from apps.projects.services import save_project
    from tests.test_projects import values

    empty = save_project(values("Empty list"), actor=actor)
    row = s.insert(empty.pk, actor=actor, expected_revision=1)
    assert row.order == 1 and row.arrangement_id is None
    with pytest.raises(ValidationError):
        s.insert(empty.pk, at=0, actor=actor, expected_revision=2)
    s.remove(empty.pk, row.pk, actor=actor, expected_revision=2)
    assert not s.positions(empty).exists()
    assert empty.positions.get().active is False
