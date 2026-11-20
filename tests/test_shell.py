"""German shell, diagnostics visibility and collected offline asset checks."""

import pytest
from django.core.management import call_command
from django.test import Client


@pytest.mark.django_db
@pytest.mark.parametrize("enabled", [False, True])
def test_diagnostics_navigation(client, django_user_model, settings, enabled):
    settings.DEBUG_MODE = enabled
    client.force_login(django_user_model.objects.create_user("synthetic"))
    body = client.get("/").content.decode()
    assert ("Debug / Logs" in body) is enabled
    assert 'aria-current="page"' in body
    assert "In Entwicklung" in body


def test_collected_stylesheet_served_by_whitenoise(settings, tmp_path):
    settings.STATIC_ROOT = tmp_path
    call_command("collectstatic", interactive=False, verbosity=0)
    response = Client().get("/static/css/base.css")
    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/css")
    content = b"".join(response.streaming_content) if response.streaming else response.content
    assert b".dashboard" in content
