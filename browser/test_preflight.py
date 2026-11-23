"""German preflight browser rejects conflicts/corruption and acknowledges missing."""

import subprocess
from pathlib import Path

import pytest
from django.core.management import call_command

from tests.test_editions import edition_inputs as _edition_fixture
from tests.test_resolution import resolver_inputs as _resolution_fixture

edition_inputs = _edition_fixture
resolver_inputs = _resolution_fixture


@pytest.mark.django_db(transaction=True)
def test_preflight_browser(resolver_inputs, settings, tmp_path, request):
    actor, project, _arr, parts, people, positions, first, *_ = resolver_inputs
    from apps.projects.models import PartOverride

    actor.set_password("Synthetic-preflight-135")
    actor.save()
    PartOverride.objects.create(
        project=project,
        position=positions[0],
        participant=people[2],
        desired_part=parts[1],
        edition=first.assignments.get(),
    )
    (settings.CURATED_DIR / first.relative_path).write_bytes(b"corrupted synthetic input")
    settings.STATIC_ROOT = tmp_path / "static"
    call_command("collectstatic", interactive=False, verbosity=0)
    server = request.getfixturevalue("live_server")
    subprocess.run(
        [
            "node",
            str(Path(__file__).with_name("preflight.cjs")),
            server.url,
            str(project.pk),
            str(people[0].pk),
            str(people[1].pk),
            str(people[2].pk),
            str(positions[0].pk),
        ],
        check=True,
        timeout=90,
    )
    project.refresh_from_db()
    assert project.revision == 1
