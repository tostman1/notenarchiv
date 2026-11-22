"""Actual shared-list reserve, repetition, live library and drag-drop preview."""

import subprocess
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from apps.catalog.models import Arrangement, Work
from apps.projects import models as m
from apps.projects import services as s
from tests.test_projects import values


@pytest.mark.django_db(transaction=True)
def test_shared_piece_list_in_browser(settings, tmp_path, request):
    settings.STATIC_ROOT = tmp_path / "static"
    call_command("collectstatic", interactive=False, verbosity=0)
    actor = get_user_model().objects.create_user("pieces-browser", password="Synthetic-pieces-135")
    project = s.save_project(values(), actor=actor)
    arr = Arrangement.objects.create(work=Work.objects.create(title="ABBA synthetic"))
    slots = [
        m.ProjectPosition.objects.create(project=project, order=n, arrangement=arr if n != 2 else None)
        for n in (1, 2, 3)
    ]
    server = request.getfixturevalue("live_server")
    subprocess.run(
        [
            "node",
            str(Path(__file__).with_name("pieces.cjs")),
            server.url,
            str(project.pk),
            *[str(row.pk) for row in slots],
        ],
        check=True,
        timeout=90,
    )
    ordered = list(project.positions.filter(active=True).order_by("order"))
    assert ordered[0].pk == slots[2].pk
    assert len(ordered) == 4 and ordered[2].arrangement_id is not None
    assert [row.order for row in ordered] == [1, 2, 3, 4]
