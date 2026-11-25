"""Release policy and container startup checks without Docker or real data."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from config.container import ensure_database_ready
from scripts.check_release import validate_tag


@pytest.mark.parametrize("tag", ["v0.1.0-preview.1", "v0.2.0-rc.2", "v0.1.0-test.1"])
def test_preview_tags_are_versioned(tag):
    assert validate_tag(tag) == tag[1:]


@pytest.mark.parametrize("tag", ["latest", "main", "v1.0.0", "v0.1.0-preview.0", "v0.1.0-preview.1\ninvalid"])
def test_stable_and_invalid_tags_are_blocked(tag):
    with pytest.raises(ValueError):
        validate_tag(tag)


def test_web_requires_initialized_database(tmp_path, monkeypatch):
    env = SimpleNamespace(database_path=tmp_path / "missing.sqlite3")
    with pytest.raises(RuntimeError, match="Initialize"):
        ensure_database_ready(env)
    assert not env.database_path.exists()
    env.database_path.touch()
    monkeypatch.chdir(tmp_path)
    calls = []
    monkeypatch.setattr("config.container.subprocess.run", lambda *args, **kwargs: calls.append((args, kwargs)))
    ensure_database_ready(env)
    assert Path(calls[0][0][0][1]) == Path(__file__).resolve().parents[1] / "manage.py"
    assert "--check" in calls[0][0][0] and calls[0][1]["timeout"] == 30


def test_private_nas_liveness_does_not_redirect_but_business_http_does(client, settings):
    settings.SECURE_SSL_REDIRECT = True
    assert client.get("/healthz", HTTP_HOST="127.0.0.1").status_code == 200
    assert client.get("/login/").status_code == 301
    assert client.get("/login/", HTTP_X_FORWARDED_PROTO="https").status_code == 200
    assert client.get("/healthz", HTTP_HOST="evil.invalid").status_code == 400
