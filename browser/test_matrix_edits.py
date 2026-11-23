"""Actual HTMX cell/default edit, reload and conflicting second browser tab."""

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
def test_direct_matrix_edits_in_browser(resolver_inputs, settings, tmp_path, request):
    actor, project, _arr, parts, people, positions, first, _second, make = resolver_inputs
    actor.set_password("Synthetic-matrix-edit-135")
    actor.save()
    make(3, part=parts[2])
    settings.STATIC_ROOT = tmp_path / "static"
    call_command("collectstatic", interactive=False, verbosity=0)
    server = request.getfixturevalue("live_server")
    subprocess.run(
        [
            "node",
            str(Path(__file__).with_name("matrix_edits.cjs")),
            server.url,
            str(project.pk),
            str(positions[0].pk),
            str(people[2].pk),
            str(first.pk),
            str(first.assignments.get().pk),
            str(parts[0].pk),
            str(positions[2].pk),
        ],
        check=True,
        timeout=90,
    )
    override = m.PartOverride.objects.get()
    assert override.position_id == positions[0].pk and override.participant_id == people[2].pk
    assert override.edition_id == first.assignments.get().pk
    people[2].refresh_from_db()
    assert people[2].default_part_id == parts[0].pk
    assert project.positions.count() == 3 and m.MatrixChange.objects.count() == 1
