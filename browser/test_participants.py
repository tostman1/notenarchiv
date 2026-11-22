"""Real German subset/guest/manual default and explicit master refresh workflow."""

import subprocess
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from apps.catalog.models import InstrumentVariant, Part
from apps.members.models import Member
from apps.projects import services as s
from tests.test_projects import values


@pytest.mark.django_db(transaction=True)
def test_participant_saved_defaults_in_browser(settings, tmp_path, request):
    settings.STATIC_ROOT = tmp_path / "static"
    call_command("collectstatic", interactive=False, verbosity=0)
    actor = get_user_model().objects.create_user("participants-browser", password="Synthetic-participants-135")
    variant = InstrumentVariant.objects.create(name="Synthetic Posaune", clef="BASS")
    parts = [Part.objects.create(instrument=variant, code=str(n)) for n in (1, 2)]
    members = [Member.objects.create(name=f"Synthetic member {n}", regular_part=parts[0]) for n in (1, 2)]
    project = s.save_project(values(), actor=actor)
    server = request.getfixturevalue("live_server")
    script = str(Path(__file__).with_name("participants.cjs"))
    args = [server.url, str(project.pk), str(members[0].pk), str(parts[0].pk), str(parts[1].pk)]
    subprocess.run(["node", script, "select", *args], check=True, timeout=90)
    participant = project.participants.get(member=members[0])
    assert participant.default_part_id == parts[0].pk
    members[0].regular_part = parts[1]
    members[0].revision += 1
    members[0].save()
    subprocess.run(["node", script, "refresh", *args], check=True, timeout=90)
    participant.refresh_from_db()
    assert participant.default_part_id == parts[1].pk and participant.active
    assert project.participants.filter(member__isnull=True).count() == 1
    assert Member.objects.count() == 2
