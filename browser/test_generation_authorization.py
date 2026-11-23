"""Browser authorization rechecks missing acknowledgements and replay identity."""

import subprocess
from pathlib import Path

import pytest
from django.core.management import call_command

from apps.exports.models import GenerationRun
from tests.test_editions import edition_inputs as _edition_fixture
from tests.test_resolution import resolver_inputs as _resolution_fixture

edition_inputs = _edition_fixture
resolver_inputs = _resolution_fixture


@pytest.mark.django_db(transaction=True)
def test_generation_authorization_browser(resolver_inputs, settings, tmp_path, request):
    actor, project, _arr, _parts, people, positions, *_ = resolver_inputs
    actor.set_password("Synthetic-snapshot-135")
    actor.save()
    settings.STATIC_ROOT = tmp_path / "static"
    call_command("collectstatic", interactive=False, verbosity=0)
    server = request.getfixturevalue("live_server")
    subprocess.run(
        [
            "node",
            str(Path(__file__).with_name("generation_authorization.cjs")),
            server.url,
            str(project.pk),
            str(people[0].pk),
        ],
        check=True,
        timeout=90,
    )
    assert GenerationRun.objects.count() == 1
    run = GenerationRun.objects.get()
    assert run.job.status == "QUEUED" and len(run.snapshot.acknowledgements) == 2
    assert run.snapshot.positions.count() == 3
