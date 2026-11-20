"""Explicit browser suite using the Django test database and a loopback server."""

import subprocess
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command


@pytest.fixture()
def shell_server(settings, tmp_path, request):
    settings.STATIC_ROOT = tmp_path / "staticfiles"
    settings.DEBUG_MODE = False
    call_command("collectstatic", interactive=False, verbosity=0)
    return request.getfixturevalue("live_server")


def test_navigation_and_authentication(shell_server):
    get_user_model().objects.create_user("smoke-archivist", password="Synthetic-smoke-135")
    subprocess.run(
        ["node", str(Path(__file__).with_name("shell.cjs")), shell_server.url],
        check=True,
        timeout=60,
    )
