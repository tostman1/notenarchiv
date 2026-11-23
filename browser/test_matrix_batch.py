"""Real same-person multi-cell HTMX save, single reset, conflict and reload."""

import subprocess
from pathlib import Path

import pytest
from django.core.management import call_command

from apps.projects import models as m
from tests.test_editions import edition_inputs as _edition_fixture
from tests.test_resolution import resolver_inputs as _resolution_fixture

edition_inputs = _edition_fixture
resolver_inputs = _resolution_fixture


@pytest.mark.django_db(transaction=True)
def test_matrix_batch_in_browser(resolver_inputs, settings, tmp_path, request):
    actor, project, _arr, parts, people, positions, first, _second, make = resolver_inputs
    actor.set_password("Synthetic-matrix-batch-135")
    actor.save()
    make(3, part=parts[2])
    settings.STATIC_ROOT = tmp_path / "static"
    call_command("collectstatic", interactive=False, verbosity=0)
    server = request.getfixturevalue("live_server")
    subprocess.run(
        [
            "node",
            str(Path(__file__).with_name("matrix_batch.cjs")),
            server.url,
            str(project.pk),
            str(people[2].pk),
            str(parts[1].pk),
            str(first.pk),
            *[str(slot.pk) for slot in positions],
        ],
        check=True,
        timeout=90,
    )
    assert not m.PartOverride.objects.filter(active=True).exists()
    assert m.PartOverride.objects.filter(active=False).count() == 2
    assert all(
        row.participant_id == people[2].pk and row.edition_id == first.assignments.get().pk
        for row in m.PartOverride.objects.all()
    )
    assert project.matrix_history.count() == 4
    project.refresh_from_db()
    assert project.revision == 4
