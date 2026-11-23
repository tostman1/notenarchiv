"""Local-only capability, manual authentication and conservative CI classification."""

import pytest

from scripts.ci_changes import docs_only
from scripts.dev import confirmed


def test_shutdown_confirmation_is_explicit():
    assert confirmed("kill", "yes")
    assert not confirmed("kill", "no")
    assert not confirmed("kill", "y")
    assert not confirmed("stop", "yes")


def test_ci_classification_fails_closed():
    assert docs_only(["docs/PROGRESS.md", "tests/TRACEABILITY.md"])
    for paths in (
        [],
        ["docs/INSTALL.md"],
        ["AGENTS.md"],
        ["apps/accounts/views.py"],
        ["docs/PROGRESS.md", ".github/workflows/ci.yml"],
    ):
        assert not docs_only(paths)


@pytest.mark.django_db
def test_local_login_capability_and_session(client, settings):
    settings.DEVELOPMENT_PROFILE = True
    settings.DEV_LOGIN_TOKEN = "synthetic-token-" * 4
    response = client.get("/dev-login/", {"token": settings.DEV_LOGIN_TOKEN}, HTTP_HOST="127.0.0.1")
    assert response.status_code == 302
    assert client.get("/", HTTP_HOST="127.0.0.1").status_code == 200
    from django.contrib.auth import get_user_model

    user = get_user_model().objects.get(username="synthetic-local-developer")
    assert not user.has_usable_password()


@pytest.mark.django_db
def test_dev_login_nas_remote_forged_denial(client, settings):
    settings.DEV_LOGIN_TOKEN = "synthetic-token-" * 4
    settings.DEVELOPMENT_PROFILE = False
    assert client.get("/dev-login/", {"token": settings.DEV_LOGIN_TOKEN}).status_code == 404
    settings.DEVELOPMENT_PROFILE = True
    assert client.get("/dev-login/", {"token": "forged"}, HTTP_HOST="127.0.0.1").status_code == 404
    assert (
        client.get(
            "/dev-login/", {"token": settings.DEV_LOGIN_TOKEN}, HTTP_HOST="127.0.0.1", REMOTE_ADDR="192.0.2.1"
        ).status_code
        == 404
    )


def test_dev_login_config_nas_rejected():
    from config.env import ConfigError, _dev_login_token

    with pytest.raises(ConfigError):
        _dev_login_token({"DEV_LOGIN_TOKEN": "x" * 40}, "nas", "127.0.0.1")
    with pytest.raises(ConfigError):
        _dev_login_token({"DEV_LOGIN_TOKEN": "x" * 40}, "local", "0.0.0.0")


@pytest.mark.django_db
def test_restart_token_preserves_only_synthetic_identity(settings):
    from django.contrib.auth import get_user_model
    from django.test import Client

    settings.DEVELOPMENT_PROFILE = True
    settings.DEV_LOGIN_TOKEN = "first-synthetic-token-" * 3
    first = Client()
    assert first.get("/dev-login/", {"token": settings.DEV_LOGIN_TOKEN}, HTTP_HOST="127.0.0.1").status_code == 302
    user_id = get_user_model().objects.get(username="synthetic-local-developer").pk
    old = settings.DEV_LOGIN_TOKEN
    settings.DEV_LOGIN_TOKEN = "new-synthetic-token-" * 3
    second = Client()
    assert second.get("/dev-login/", {"token": old}, HTTP_HOST="127.0.0.1").status_code == 404
    assert second.get("/dev-login/", {"token": settings.DEV_LOGIN_TOKEN}, HTTP_HOST="127.0.0.1").status_code == 302
    assert get_user_model().objects.get(username="synthetic-local-developer").pk == user_id


def test_diagnostics_never_expose_raw_request_secrets():
    import json
    import logging
    from types import SimpleNamespace

    from config.diagnostics import DiagnosticFormatter

    record = logging.LogRecord("django.request", logging.WARNING, "", 1, "private", (), None)
    record.status_code = 404
    record.request = SimpleNamespace(path="/members/private-name/", resolver_match=None, META={"token": "secret"})
    result = json.loads(DiagnosticFormatter("web").format(record))
    assert result["endpoint"] == "unmatched-route"
    assert "private-name" not in str(result) and "secret" not in str(result)
