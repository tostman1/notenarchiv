"""German role creation/mapping/assignment and exact variant rejection in browser."""

import subprocess
import uuid
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from apps.catalog.models import Arrangement, InstrumentVariant, Part, Work
from apps.projects import models as m
from apps.projects import services as s
from tests.test_projects import values


@pytest.mark.django_db(transaction=True)
def test_ensemble_editor_browser(settings, tmp_path, request):
    settings.STATIC_ROOT = tmp_path / "static"
    call_command("collectstatic", interactive=False, verbosity=0)
    actor = get_user_model().objects.create_user("ensemble-browser", password="Synthetic-ensemble-135")
    project = s.save_project(values(), actor=actor)
    variants = [
        InstrumentVariant.objects.create(name=name, clef=clef, transposition=key)
        for name, clef, key in [("Posaune", "BASS", "C"), ("Tenorhorn", "TREBLE", "B")]
    ]
    parts = [Part.objects.create(instrument=variant, code="3") for variant in variants]
    people = [
        m.ProjectParticipant.objects.create(
            project=project, guest_id=uuid.uuid4(), display_name=f"Synthetic musician {n}", default_part=part
        )
        for n, part in enumerate(parts)
    ]
    position = m.ProjectPosition.objects.create(
        project=project,
        order=1,
        arrangement=Arrangement.objects.create(work=Work.objects.create(title="Synthetic piece")),
    )
    server = request.getfixturevalue("live_server")
    subprocess.run(
        [
            "node",
            str(Path(__file__).with_name("ensemble.cjs")),
            server.url,
            str(project.pk),
            *[str(person.pk) for person in people],
            *[str(variant.pk) for variant in variants],
            *[str(part.pk) for part in parts],
            str(position.pk),
        ],
        check=True,
        timeout=90,
    )
    role = project.roles.get()
    assert project.participants.filter(role=role).count() == 2
    assert m.EnsembleMapping.objects.filter(project=project).count() == 3
    assert m.EnsembleMapping.objects.filter(project=project, active=True).count() == 2
    assert [person.default_part_id for person in project.participants.order_by("display_name")] == [
        part.pk for part in parts
    ]
