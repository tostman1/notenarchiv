"""German project CRUD/duplication/archive with optimistic browser conflicts."""

import subprocess
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from apps.projects.models import Project


@pytest.mark.django_db(transaction=True)
def test_project_crud_in_browser(settings, tmp_path, request):
    settings.STATIC_ROOT = tmp_path / "static"
    call_command("collectstatic", interactive=False, verbosity=0)
    get_user_model().objects.create_user("projects-browser", password="Synthetic-projects-135")
    server = request.getfixturevalue("live_server")
    subprocess.run(["node", str(Path(__file__).with_name("projects.cjs")), server.url], check=True, timeout=90)
    assert Project.objects.count() == 2
    assert Project.objects.get(duplicated_from__isnull=True).name == "Synthetic changed"
    assert Project.objects.get(duplicated_from__isnull=False).status == "ARCHIVED"
