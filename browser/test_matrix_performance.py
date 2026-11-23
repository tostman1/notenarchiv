"""Navigate/filter a synthetic 100-position, 50-participant project in Chrome."""

import subprocess
import uuid
from pathlib import Path

import pytest
from django.core.management import call_command

from apps.projects import models as m
from tests.test_editions import edition_inputs as _edition_fixture
from tests.test_resolution import resolver_inputs as _resolution_fixture

edition_inputs = _edition_fixture
resolver_inputs = _resolution_fixture


@pytest.mark.django_db(transaction=True)
def test_large_matrix_browser(resolver_inputs, settings, tmp_path, request):
    actor, project, arr, parts, people, positions, first, *_ = resolver_inputs
    actor.set_password("Synthetic-matrix-performance-135")
    actor.save()
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
            str(Path(__file__).with_name("matrix_performance.cjs")),
            server.url,
            str(project.pk),
            str(people[2].pk),
            str(parts[0].instrument_id),
        ],
        check=True,
        timeout=120,
    )
    project.refresh_from_db()
    assert project.revision == 1 and project.positions.count() == 100 and project.participants.count() == 50
