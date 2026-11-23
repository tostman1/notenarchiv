"""Synthetic filters and SQL growth measurements through fully rendered responses."""

import time
import uuid

import pytest
from django.core.exceptions import ValidationError
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.projects import models as m
from apps.projects.matrix_edit_context import add_edit_forms
from apps.projects.matrix_services import matrix_page
from tests.test_resolution import resolver_inputs as _resolution_fixture

resolver_inputs = _resolution_fixture


def test_header_choice_inventory_is_bounded(resolver_inputs, monkeypatch):
    actor, project, *_ = resolver_inputs
    import apps.projects.matrix_edit_context as context_module

    # Repeated presentation rows model an oversized catalog without real data.
    class Inventory:
        def select_related(self, *args):
            return self

        def order_by(self, *args):
            return self

        def __getitem__(self, key):
            return [None] * 2001

    context = matrix_page(project.pk)
    monkeypatch.setattr(context_module.Part.objects, "filter", lambda **kwargs: Inventory())
    with pytest.raises(ValidationError, match="inventory limit"):
        add_edit_forms(context, actor)


def test_filters_preserve_shared_list_and_absolute_numbers(resolver_inputs, client):
    actor, project, _arr, parts, people, positions, first, *_ = resolver_inputs
    client.force_login(actor)
    url = reverse("project_matrix", args=[project.pk])
    choice = first.assignments.get()
    m.PartOverride.objects.create(
        project=project, position=positions[0], participant=people[2], desired_part=parts[1], edition=choice
    )
    response = client.get(url, {"participant": people[2].pk, "deviation": "personal"})
    assert response.status_code == 200
    assert [row["position"].order for row in response.context["rows"]] == [1]
    assert [row.pk for row in response.context["participants"]] == [people[2].pk]
    assert response.context["rows"][0]["cells"][0]["resolution"].assignment_id == choice.pk
    response = client.get(url, {"q": "math", "instrument": parts[0].instrument_id})
    assert [row.pk for row in response.context["participants"]] == [people[0].pk]
    assert project.positions.count() == 3 and project.participants.count() == 3
    assert project.revision == 1
    assert client.get(url, {"instrument": "invalid"}).status_code == 400
    assert client.get(url, {"deviation": "invented"}).status_code == 400


def test_htmx_navigation_and_edits_retain_filters(resolver_inputs, client):
    actor, project, _arr, parts, people, *_ = resolver_inputs
    client.force_login(actor)
    response = client.get(reverse("project_matrix", args=[project.pk]), {"q": "Riccardo"}, HTTP_HX_REQUEST="true")
    assert response.status_code == 200 and b"<html" not in response.content
    assert b'name="q" value="Riccardo"' in response.content
    prefix = f"default-{people[2].pk}"
    response = client.post(
        reverse("matrix_default_edit", args=[project.pk, people[2].pk]),
        {
            prefix + "-part": parts[0].pk,
            prefix + "-expected_revision": 1,
            "q": "Riccardo",
        },
        HTTP_HX_REQUEST="true",
    )
    assert response.status_code == 200
    assert len(response.context["participants"]) == 1
    assert response.context["navigation"] == {"q": "Riccardo"}


def test_issue_and_deviation_filters_keep_resolver_and_reserves(resolver_inputs, client):
    actor, project, _arr, parts, people, *_ = resolver_inputs
    client.force_login(actor)
    url = reverse("project_matrix", args=[project.pk])
    for mode in ("issues", "deviations"):
        response = client.get(url, {"deviation": mode})
        assert response.status_code == 200
        assert [row["position"].order for row in response.context["rows"]] == [1, 2]
        for row in response.context["rows"]:
            for cell in row["cells"]:
                assert cell["resolution"].status in {"MISSING", "AMBIGUOUS"}
                assert cell["filter_match"] and cell["deviation"]
    response = client.get(url, {"participant": uuid.uuid4()})
    assert response.status_code == 200 and response.context["participants"] == []
    assert project.positions.count() == 3


def test_synthetic_100_by_50_bounded_render_queries(resolver_inputs, client, capsys):
    actor, project, arr, parts, people, positions, first, *_ = resolver_inputs
    client.force_login(actor)
    url = reverse("project_matrix", args=[project.pk])

    def measure():
        start = time.perf_counter()
        with CaptureQueriesContext(connection) as queries:
            response = client.get(url)
        assert response.status_code == 200
        return len(queries), time.perf_counter() - start, len(response.content)

    small = measure()
    m.ProjectPosition.objects.bulk_create(
        [m.ProjectPosition(project=project, order=number, arrangement=arr) for number in range(4, 101)]
    )
    m.ProjectParticipant.objects.bulk_create(
        [
            m.ProjectParticipant(
                project=project, guest_id=uuid.uuid4(), display_name=f"Synthetic {number:02}", default_part=parts[1]
            )
            for number in range(47)
        ]
    )
    large = measure()
    # Same two physical edition alternatives, more rendered cells: no per-cell SQL.
    assert large[0] == small[0]
    response = client.get(url, {"rows": 4, "people": 5})
    assert response.context["row_page"].paginator.count == 100
    assert response.context["column_page"].paginator.count == 50
    assert response.context["rows"][0]["position"].order == 76
    assert len(response.context["rows"]) == 25 and len(response.context["participants"]) == 10
    # Captured test output is an aggregate of deterministic synthetic data only.
    with capsys.disabled():
        import sys

        sys.stdout.write(f"\nMATRIX_METRICS small={small!r} 100x50_window={large!r}\n")
