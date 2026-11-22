"""Read-only matrix uses the resolver, with stable shared rows and exact provenance."""

import uuid

from django.urls import reverse

from apps.archive import edition_services
from apps.projects import matrix_services as s
from apps.projects import models as m
from apps.projects import resolution_services as r
from apps.projects import rule_services
from tests.test_resolution import resolver_inputs as _resolution_fixture

resolver_inputs = _resolution_fixture


def test_matrix_mathias_sebi_riccardo_shared_rows_and_personal_part(resolver_inputs, client):
    actor, project, arr, parts, people, positions, first, _second, make = resolver_inputs
    make(3, part=parts[2])
    m.PartOverride.objects.create(
        project=project,
        position=positions[0],
        participant=people[2],
        desired_part=parts[1],
        edition=first.assignments.get(),
    )
    client.force_login(actor)
    response = client.get(reverse("project_matrix", args=[project.pk]))
    assert response.status_code == 200
    assert len(response.context["rows"]) == 3 and len(response.context["participants"]) == 3
    cells = {cell["resolution"].participant_id: cell for cell in response.context["rows"][0]["cells"]}
    assert cells[people[0].pk]["resolution"].status == "MISSING"
    assert cells[people[1].pk]["resolution"].status == "AMBIGUOUS"
    assert cells[people[2].pk]["resolution"].effective_part_id == parts[1].pk
    assert cells[people[2].pk]["resolution"].edition_origin == "PERSONAL"
    html = response.content.decode()
    assert "Persönlicher Stück-Override" in html and "Gespeicherter Projektdefault" in html
    assert "Musikalische Rolle" not in html
    assert "Noten fehlen" in html and "Mehrere Ausgaben" in html


def test_matrix_is_resolver_output_not_second_algorithm(resolver_inputs, client, monkeypatch):
    actor, project, arr, parts, people, positions, first, *_ = resolver_inputs
    client.force_login(actor)
    called = []
    original = r.ResolutionSession.verified_resolution

    def resolve(self, position, person):
        called.append((position, person))
        return original(self, position, person)

    monkeypatch.setattr(r.ResolutionSession, "verified_resolution", resolve)
    response = client.get(reverse("project_matrix", args=[project.pk]))
    assert len(called) == 9
    for row in response.context["rows"]:
        for cell in row["cells"]:
            result = cell["resolution"]
            assert result == r.resolve_cell(project.pk, row["position"].pk, result.participant_id)
    assert project.revision == 1 and project.history.count() == 1


def test_reserve_cells_readonly_no_preview_or_assignment_forms(resolver_inputs, client):
    actor, project, _arr, _parts, _people, positions, *_ = resolver_inputs
    client.force_login(actor)
    response = client.get(reverse("project_matrix", args=[project.pk]))
    reserve = response.context["rows"][2]
    assert reserve["position"].pk == positions[2].pk
    assert all(cell["resolution"].status == "RESERVE" for cell in reserve["cells"])
    assert all(cell["resolution"].file_id is None for cell in reserve["cells"])
    from html.parser import HTMLParser

    class Forms(HTMLParser):
        def __init__(self):
            super().__init__()
            self.actions = []

        def handle_starttag(self, tag, attrs):
            if tag == "form":
                self.actions.append(dict(attrs).get("action"))

    parser = Forms()
    parser.feed(response.content.decode())
    assert parser.actions == [reverse("logout")]


def test_matrix_selected_only_auth_post_denial_and_safe_names(resolver_inputs, client):
    actor, project, _arr, parts, people, positions, *_ = resolver_inputs
    url = reverse("project_matrix", args=[project.pk])
    assert client.get(url).status_code == 302
    client.force_login(actor)
    m.ProjectParticipant.objects.filter(pk=people[0].pk).update(active=False)
    m.ProjectParticipant.objects.filter(pk=people[1].pk).update(display_name="<script>Synthetic</script>")
    response = client.get(url)
    assert len(response.context["participants"]) == 2
    assert "&lt;script&gt;" in response.content.decode() and "no-store" in response["Cache-Control"]
    assert client.post(url, {}).status_code == 405


def test_matrix_pagination_keeps_absolute_common_numbers_and_people(resolver_inputs, client):
    actor, project, arr, parts, people, positions, *_ = resolver_inputs
    for n in range(4, 29):
        m.ProjectPosition.objects.create(project=project, order=n, arrangement=None)
    for n in range(12):
        m.ProjectParticipant.objects.create(
            project=project, guest_id=uuid.uuid4(), display_name=f"Synthetic {n}", default_part=parts[0]
        )
    client.force_login(actor)
    response = client.get(reverse("project_matrix", args=[project.pk]), {"rows": 2, "people": 2})
    assert len(response.context["rows"]) == 3 and response.context["rows"][0]["position"].order == 26
    assert len(response.context["participants"]) == 5
    assert response.context["column_page"].paginator.count == 15
    assert project.positions.filter(active=True).count() == 28


def test_matrix_substitution_and_corrupt_pin_clear_status(resolver_inputs, client, settings):
    actor, project, arr, parts, people, positions, first, *_ = resolver_inputs
    edition_services.set_preference(
        arr.pk, parts[1].pk, first.assignments.get().pk, actor=actor, expected_revision=arr.revision
    )
    rule_services.save_replacement(
        project_id=project.pk,
        desired_part_id=parts[2].pk,
        replacement_part_id=parts[1].pk,
        actor=actor,
        expected_revision=1,
    )
    client.force_login(actor)
    response = client.get(reverse("project_matrix", args=[project.pk]))
    cell = next(
        cell for cell in response.context["rows"][0]["cells"] if cell["resolution"].participant_id == people[2].pk
    )
    assert cell["resolution"].status == "SUBSTITUTED" and cell["replacement_label"] == "Projekt-Ersatzregel"
    (settings.CURATED_DIR / first.relative_path).write_bytes(b"corrupt synthetic")
    response = client.get(reverse("project_matrix", args=[project.pk]))
    cell = next(
        cell for cell in response.context["rows"][0]["cells"] if cell["resolution"].participant_id == people[1].pk
    )
    assert cell["resolution"].status == "CORRUPT"
    assert "Bestätigte PDF herunterladen" not in response.content.decode()


def test_matrix_empty_project_and_archived_project_are_readonly(resolver_inputs, client):
    actor, project, *_ = resolver_inputs
    from apps.projects.services import archive_project, save_project
    from tests.test_projects import values

    empty = save_project(values("Empty synthetic matrix"), actor=actor)
    client.force_login(actor)
    response = client.get(reverse("project_matrix", args=[empty.pk]))
    assert response.status_code == 200 and not response.context["rows"]
    archive_project(project.pk, actor=actor, expected_revision=1)
    response = client.get(reverse("project_matrix", args=[project.pk]))
    assert response.status_code == 200 and "Archiviert" in response.content.decode()


def test_matrix_boundary_calls_verified_once_per_shared_file(resolver_inputs, monkeypatch):
    actor, project, arr, parts, people, positions, first, *_ = resolver_inputs
    edition_services.set_preference(
        arr.pk, parts[1].pk, first.assignments.get().pk, actor=actor, expected_revision=arr.revision
    )
    for person in people:
        m.ProjectParticipant.objects.filter(pk=person.pk).update(default_part=parts[1])
    calls = []
    original = r.library_services.verify_file

    def verified(file):
        calls.append(file.pk)
        return original(file)

    monkeypatch.setattr(r.library_services, "verify_file", verified)
    context = s.matrix_page(project.pk)
    assert calls == [first.pk]
    assert all(cell["resolution"].usable for row in context["rows"][:2] for cell in row["cells"])


def test_matrix_missing_role_is_visible_without_silent_saved_default(resolver_inputs, client):
    actor, project, _arr, parts, people, positions, *_ = resolver_inputs
    from apps.projects import ensemble_services

    role = ensemble_services.save_role(project.pk, code="3", label="Synthetic role", actor=actor, expected_revision=1)
    ensemble_services.assign_role(project.pk, people[1].pk, role.pk, actor=actor, expected_revision=2)
    client.force_login(actor)
    response = client.get(reverse("project_matrix", args=[project.pk]))
    cell = next(
        cell for cell in response.context["rows"][0]["cells"] if cell["resolution"].participant_id == people[1].pk
    )
    assert cell["resolution"].status == "MAPPING_MISSING" and cell["effective_part"] is None
    assert "Musikalische Rolle" in response.content.decode() and "Ensemble-Mapping fehlt" in response.content.decode()


def test_matrix_revalidation_remains_visible_and_no_invalid_download(resolver_inputs, client):
    actor, project, _arr, parts, people, positions, first, *_ = resolver_inputs
    override = m.PartOverride.objects.create(
        project=project,
        position=positions[0],
        participant=people[2],
        desired_part=parts[1],
        edition=first.assignments.get(),
    )
    m.PartOverride.objects.filter(pk=override.pk).update(needs_revalidation=True)
    client.force_login(actor)
    response = client.get(reverse("project_matrix", args=[project.pk]))
    cell = next(
        cell for cell in response.context["rows"][0]["cells"] if cell["resolution"].participant_id == people[2].pk
    )
    assert cell["resolution"].status == "INVALID" and cell["resolution"].override_id == override.pk
    assert "Persönlichen Override nach Arrangementwechsel erneut prüfen" in response.content.decode()


def test_matrix_link_and_unknown_project_denial(resolver_inputs, client):
    actor, project, *_ = resolver_inputs
    client.force_login(actor)
    detail = client.get(reverse("project_detail", args=[project.pk]))
    assert reverse("project_matrix", args=[project.pk]) in detail.content.decode()
    assert client.get(reverse("project_matrix", args=[uuid.uuid4()])).status_code == 404
