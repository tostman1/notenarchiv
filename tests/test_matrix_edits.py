"""Exact manual cell/default edits preserve other people, shared slots and history."""

import uuid

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import Client
from django.urls import reverse

from apps.archive import services as review
from apps.projects import matrix_edit_services as s
from apps.projects import models as m
from apps.projects import resolution_services as r
from apps.projects.matrix_edit_context import add_edit_forms
from apps.projects.matrix_services import matrix_page
from apps.projects.services import ProjectConflict, archive_project, save_project
from tests.test_projects import values
from tests.test_resolution import resolver_inputs as _resolution_fixture

resolver_inputs = _resolution_fixture


def payload(position, person, token, revision=1):
    prefix = f"cell-{position.pk}-{person.pk}"
    return {
        prefix + "-choice": token,
        prefix + "-expected_revision": revision,
        prefix + "-rows": 1,
        prefix + "-people": 1,
    }


def test_manual_part_two_and_notation_exact_version_other_cells_unchanged(resolver_inputs):
    actor, project, arr, parts, people, positions, first, _second, make = resolver_inputs
    make(3, part=parts[2])
    before = list(project.positions.values_list("pk", "order")), people[2].default_part_id
    record = s.set_cell(
        project.pk,
        positions[0].pk,
        people[2].pk,
        s.choice_token(first.assignments.get(), actor),
        actor=actor,
        expected_revision=1,
    )
    result = r.resolve_cell(project.pk, positions[0].pk, people[2].pk)
    assert result.usable and result.edition_origin == "PERSONAL" and result.effective_part_id == parts[1].pk
    assert not m.PartOverride.objects.filter(participant=people[1]).exists()
    assert not m.PartOverride.objects.filter(position=positions[1]).exists()
    assert list(project.positions.values_list("pk", "order")) == before[0]
    people[2].refresh_from_db()
    assert people[2].default_part_id == before[1]
    foreign = make(4, part=parts[3])
    updated = s.set_cell(
        project.pk,
        positions[0].pk,
        people[2].pk,
        s.choice_token(foreign.assignments.get(), actor),
        actor=actor,
        expected_revision=2,
    )
    assert updated.pk == record.pk and updated.desired_part_id == parts[3].pk
    assert r.resolve_cell(project.pk, positions[0].pk, people[2].pk).file_id == foreign.pk
    assert project.matrix_history.filter(previous_edition=first.assignments.get()).exists()


def test_stale_foreign_cell_reserve_invalid_actor_token_rejected(resolver_inputs):
    actor, project, arr, parts, people, positions, first, *_ = resolver_inputs
    token = s.choice_token(first.assignments.get(), actor)
    for position, person in [(positions[2].pk, people[2].pk), (positions[0].pk, uuid.uuid4())]:
        with pytest.raises(ValidationError):
            s.set_cell(project.pk, position, person, token, actor=actor, expected_revision=1)
    other = save_project(values("Other"), actor=actor)
    with pytest.raises(ValidationError):
        s.set_cell(other.pk, positions[0].pk, people[2].pk, token, actor=actor, expected_revision=1)
    outsider = get_user_model().objects.create_user("synthetic-matrix-other")
    with pytest.raises(ValidationError):
        s.selected_choice(token, outsider)
    s.set_cell(project.pk, positions[0].pk, people[2].pk, token, actor=actor, expected_revision=1)
    with pytest.raises(ProjectConflict):
        s.set_cell(project.pk, positions[1].pk, people[2].pk, token, actor=actor, expected_revision=1)
    assert m.PartOverride.objects.count() == 1


@pytest.mark.parametrize("change", ["withdrawn", "corrupt", "revision", "inactive"])
def test_selected_edition_changed_rejected_no_implicit_substitution(resolver_inputs, settings, change):
    actor, project, arr, parts, people, positions, first, *_ = resolver_inputs
    assignment = first.assignments.get()
    token = s.choice_token(assignment, actor)
    if change == "withdrawn":
        review.withdraw(first.pk, actor=actor, expected_revision=first.revision)
    elif change == "corrupt":
        (settings.CURATED_DIR / first.relative_path).write_bytes(b"synthetic corrupt")
    elif change == "inactive":
        parts[1].active = False
        parts[1].save()
    else:
        from apps.archive.models import ArchiveFile

        ArchiveFile.objects.filter(pk=first.pk).update(revision=first.revision + 1)
    with pytest.raises(ValidationError):
        s.set_cell(project.pk, positions[0].pk, people[2].pk, token, actor=actor, expected_revision=1)
    assert not m.PartOverride.objects.exists()
    project.refresh_from_db()
    assert project.revision == 1


def test_hash_race_and_audit_failure_atomic(resolver_inputs, monkeypatch):
    actor, project, arr, parts, people, positions, first, *_ = resolver_inputs
    token = s.choice_token(first.assignments.get(), actor)
    original = s.library_services.verify_file

    def changed(file):
        result = original(file)
        review.withdraw(file.pk, actor=actor, expected_revision=file.revision)
        return result

    monkeypatch.setattr(s.library_services, "verify_file", changed)
    with pytest.raises(ProjectConflict):
        s.set_cell(project.pk, positions[0].pk, people[2].pk, token, actor=actor, expected_revision=1)
    assert not m.PartOverride.objects.exists()


def test_edit_forms_only_confirmed_variants_and_reserve_no_editor(resolver_inputs):
    actor, project, arr, parts, people, positions, first, _second, make = resolver_inputs
    pending = make(3, confirmed=False)
    context = add_edit_forms(matrix_page(project.pk), actor)
    assert all("edit_form" not in cell for cell in context["rows"][2]["cells"])
    form = context["rows"][0]["cells"][0]["edit_form"]
    choices = list(form.fields["choice"].widget.choices)
    assert len(choices) == 3  # blank plus two confirmed concrete versions
    assert str(pending.pk) not in str(choices)
    assert all(person.matrix_default_form for person in context["participants"])


def test_auth_csrf_htmx_success_stale_error_and_default_keeps_override(resolver_inputs, client):
    actor, project, arr, parts, people, positions, first, *_ = resolver_inputs
    url = reverse("matrix_cell_edit", args=[project.pk, positions[0].pk, people[2].pk])
    token = s.choice_token(first.assignments.get(), actor)
    data = payload(positions[0], people[2], token)
    assert client.post(url, data).status_code == 302
    client.force_login(actor)
    csrf = Client(enforce_csrf_checks=True)
    csrf.force_login(actor)
    assert csrf.post(url, data).status_code == 403
    response = client.post(url, data, HTTP_HX_REQUEST="true")
    assert response.status_code == 200 and response.context["project"].revision == 2
    assert "Persönliche Stimme und exakte Ausgabe gespeichert" in response.content.decode()
    assert client.post(url, data, HTTP_HX_REQUEST="true").status_code == 409
    default = reverse("matrix_default_edit", args=[project.pk, people[2].pk])
    prefix = f"default-{people[2].pk}"
    response = client.post(
        default, {prefix + "-part": str(parts[0].pk), prefix + "-expected_revision": 2}, HTTP_HX_REQUEST="true"
    )
    assert response.status_code == 200 and m.PartOverride.objects.get().edition_id == first.assignments.get().pk
    assert r.resolve_cell(project.pk, positions[0].pk, people[2].pk).effective_part_id == parts[1].pk
    assert client.get(url).status_code == 405


def test_invalid_token_archived_write_and_non_htmx_redirect(resolver_inputs, client):
    actor, project, arr, parts, people, positions, first, *_ = resolver_inputs
    client.force_login(actor)
    url = reverse("matrix_cell_edit", args=[project.pk, positions[0].pk, people[2].pk])
    assert client.post(url, payload(positions[0], people[2], "invalid")).status_code == 400
    response = client.post(url, payload(positions[0], people[2], s.choice_token(first.assignments.get(), actor)))
    assert response.status_code == 302 and response.url.startswith(reverse("project_matrix", args=[project.pk]))
    archive_project(project.pk, actor=actor, expected_revision=2)
    assert (
        client.post(
            url, payload(positions[0], people[2], s.choice_token(first.assignments.get(), actor), 3)
        ).status_code
        == 409
    )


def test_audit_failure_rolls_back_saved_override_and_project_revision(resolver_inputs, monkeypatch):
    actor, project, _arr, _parts, people, positions, first, *_ = resolver_inputs

    def failed(*args, **kwargs):
        raise ValidationError("synthetic matrix history failure")

    monkeypatch.setattr(m.MatrixChange.objects, "create", failed)
    with pytest.raises(ValidationError):
        s.set_cell(
            project.pk,
            positions[0].pk,
            people[2].pk,
            s.choice_token(first.assignments.get(), actor),
            actor=actor,
            expected_revision=1,
        )
    assert not m.PartOverride.objects.exists()
    project.refresh_from_db()
    assert project.revision == 1 and project.history.count() == 1


def test_expired_token_and_inactive_participant_not_accepted(resolver_inputs, monkeypatch):
    actor, project, _arr, _parts, people, positions, first, *_ = resolver_inputs
    token = s.choice_token(first.assignments.get(), actor)
    from django.core import signing

    def expired(*args, **kwargs):
        raise signing.SignatureExpired("synthetic expiry")

    with monkeypatch.context() as patch:
        patch.setattr(s.signing, "loads", expired)
        with pytest.raises(ValidationError):
            s.selected_choice(token, actor)
    m.ProjectParticipant.objects.filter(pk=people[2].pk).update(active=False)
    with pytest.raises(ValidationError):
        s.set_cell(project.pk, positions[0].pk, people[2].pk, token, actor=actor, expected_revision=1)
    assert not m.PartOverride.objects.exists()


def test_wrong_arrangement_and_stale_default_do_not_modify_other_data(resolver_inputs, client):
    actor, project, arr, parts, people, positions, first, *_ = resolver_inputs
    from apps.catalog.models import Arrangement

    other = Arrangement.objects.create(work=arr.work, edition="Synthetic incompatible")
    foreign_slot = m.ProjectPosition.objects.create(project=project, order=4, arrangement=other)
    with pytest.raises(ValidationError):
        s.set_cell(
            project.pk,
            foreign_slot.pk,
            people[2].pk,
            s.choice_token(first.assignments.get(), actor),
            actor=actor,
            expected_revision=1,
        )
    client.force_login(actor)
    prefix = f"default-{people[2].pk}"
    url = reverse("matrix_default_edit", args=[project.pk, people[2].pk])
    assert client.post(url, {prefix + "-part": str(parts[0].pk), prefix + "-expected_revision": 999}).status_code == 409
    people[2].refresh_from_db()
    assert people[2].default_part_id == parts[2].pk


def test_alternative_bounds_fail_explicitly_not_truncate(resolver_inputs, monkeypatch):
    actor, project, *_ = resolver_inputs
    import apps.projects.matrix_edit_context as context_module

    monkeypatch.setattr(context_module, "MAX_CHOICES_PER_ARRANGEMENT", 1)
    with pytest.raises(ValidationError):
        add_edit_forms(matrix_page(project.pk), actor)


def test_alternative_byte_budget_and_safe_pagination_redirect(resolver_inputs, client, monkeypatch):
    actor, project, _arr, parts, people, positions, first, *_ = resolver_inputs
    import apps.projects.matrix_edit_context as context_module

    with monkeypatch.context() as patch:
        patch.setattr(context_module, "MAX_ALTERNATIVE_BYTES", 1)
        with pytest.raises(ValidationError):
            add_edit_forms(matrix_page(project.pk), actor)
    client.force_login(actor)
    prefix = f"default-{people[2].pk}"
    response = client.post(
        reverse("matrix_default_edit", args=[project.pk, people[2].pk]),
        {
            prefix + "-part": str(parts[0].pk),
            prefix + "-expected_revision": 1,
            "rows": "1&people=evil",
            "people": "https://invalid.example",
        },
    )
    assert response.status_code == 302 and response.url.endswith("?rows=1&people=1")


def test_archived_matrix_renders_no_mutation_forms(resolver_inputs, client):
    actor, project, *_ = resolver_inputs
    archive_project(project.pk, actor=actor, expected_revision=1)
    client.force_login(actor)
    response = client.get(reverse("project_matrix", args=[project.pk]))
    html = response.content.decode()
    assert "matrix-cell-form" not in html and "matrix-default-form" not in html
