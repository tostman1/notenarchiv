"""German matrix display with exact personal override and reserve rows."""

import subprocess
from pathlib import Path

import pytest
from django.core.management import call_command

from apps.projects import models as m
from tests.test_editions import edition_inputs as _edition_fixture
from tests.test_resolution import resolver_inputs as _resolution_fixture

resolver_inputs = _resolution_fixture
edition_inputs = _edition_fixture


@pytest.mark.django_db(transaction=True)
def test_matrix_provenance_browser(resolver_inputs, settings, tmp_path, request):
    actor, project, arr, parts, people, positions, first, _second, make = resolver_inputs
    actor.set_password("Synthetic-matrix-135")
    actor.save()
    make(3, part=parts[2])
    m.PartOverride.objects.create(
        project=project,
        position=positions[0],
        participant=people[2],
        desired_part=parts[1],
        edition=first.assignments.get(),
    )
    settings.STATIC_ROOT = tmp_path / "static"
    call_command("collectstatic", interactive=False, verbosity=0)
    server = request.getfixturevalue("live_server")
    subprocess.run(
        [
            "node",
            str(Path(__file__).with_name("matrix.cjs")),
            server.url,
            str(project.pk),
            str(positions[0].pk),
            str(people[2].pk),
            str(first.pk),
            str(positions[2].pk),
        ],
        check=True,
        timeout=90,
    )
    project.refresh_from_db()
    assert project.revision == 1 and project.positions.count() == 3
