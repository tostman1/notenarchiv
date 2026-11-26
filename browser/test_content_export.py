"""Real-browser content selection authorizes once without approving music."""

import subprocess
from pathlib import Path

import pytest
from django.core.management import call_command

from apps.exports.models import GenerationSnapshot
from tests.test_content_export import confirmed
from tests.test_editions import edition_inputs as legacy_inputs

edition_inputs = legacy_inputs


@pytest.mark.django_db(transaction=True)
def test_explicit_content_export_in_browser(edition_inputs, settings, tmp_path, request):
    identity, *_ = confirmed(edition_inputs)
    actor = edition_inputs[0]
    actor.set_password("Synthetic-content-135")
    actor.save()
    settings.STATIC_ROOT = tmp_path / "static"
    call_command("collectstatic", interactive=False, verbosity=0)
    server = request.getfixturevalue("live_server")
    subprocess.run(
        ["node", str(Path(__file__).with_name("content_export.cjs")), server.url, str(identity.pk)],
        check=True,
        timeout=90,
    )
    snapshot = GenerationSnapshot.objects.get()
    assert snapshot.payload["schema"] == 2
    assert snapshot.content_inputs.count() == 1
    assert snapshot.run.job.status == "QUEUED"
