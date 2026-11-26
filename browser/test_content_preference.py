"""Real-browser preference updates preserve CAS fencing and append-only history."""

import subprocess
from pathlib import Path

import pytest
from django.core.management import call_command

from apps.archive.models import EditionPreferenceChange, PreferredEdition
from apps.exports.models import GenerationSnapshot
from tests.test_content_export import confirmed
from tests.test_editions import edition_inputs as legacy_inputs

edition_inputs = legacy_inputs


@pytest.mark.django_db(transaction=True)
def test_content_preference_in_browser(edition_inputs, settings, tmp_path, request):
    identity, *_ = confirmed(edition_inputs)
    actor = edition_inputs[0]
    actor.set_password("Synthetic-content-135")
    actor.save()
    settings.STATIC_ROOT = tmp_path / "static"
    call_command("collectstatic", interactive=False, verbosity=0)
    server = request.getfixturevalue("live_server")
    subprocess.run(
        ["node", str(Path(__file__).with_name("content_preference.cjs")), server.url, str(identity.pk)],
        check=True,
        timeout=90,
    )
    preference = PreferredEdition.objects.get(arrangement=identity.arrangement, part=identity.part)
    assert preference.content_edition_id is None
    assert preference.assignment_id is None
    changes = list(EditionPreferenceChange.objects.order_by("created_at", "id"))
    assert len(changes) == 2
    assert changes[0].selected_content_id == identity.pk
    assert changes[1].previous_content_id == identity.pk
    assert changes[1].selected_content_id is None
    assert not GenerationSnapshot.objects.exists()
