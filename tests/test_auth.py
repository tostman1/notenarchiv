"""Authentication and session baseline tests (WP-03, UI-01, OP-03)."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from apps.accounts import services

User = get_user_model()


@pytest.fixture()
def archivist(db) -> User:
    return User.objects.create_user("archivar1", password="Korrekt!1234")


@pytest.mark.django_db
class TestProtection:
    def test_unauthenticated_root_redirects_to_login(self, client, archivist) -> None:
        response = client.get("/")
        assert response.status_code == 302
        assert response.url == reverse("login") + "?next=/"

    def test_authenticated_root_is_available(self, client, archivist) -> None:
        client.force_login(archivist)
        response = client.get("/")
        assert response.status_code == 200
        assert archivist.username.encode() in response.content

    def test_healthz_stays_public_when_business_is_protected(self, client, archivist) -> None:
        assert client.get("/healthz").status_code == 200

    def test_login_page_requires_no_authentication(self, client) -> None:
        response = client.get(reverse("login"))
        assert response.status_code == 200
        # German UI (UI-02)
        assert "Anmelden" in response.content.decode("utf-8")
        assert "Benutzername" in response.content.decode("utf-8")
        assert "Passwort" in response.content.decode("utf-8")


@pytest.mark.django_db
class TestLogin:
    def test_valid_login_reaches_next(self, client, archivist) -> None:
        response = client.post(
            reverse("login"),
            {"username": "archivar1", "password": "Korrekt!1234", "next": "/"},
        )
        assert response.status_code == 302
        assert response.url == "/"
        assert client.get("/").status_code == 200

    def test_invalid_login_shows_german_error(self, client, archivist) -> None:
        response = client.post(reverse("login"), {"username": "archivar1", "password": "falsch"})
        assert response.status_code == 200
        body = response.content.decode("utf-8")
        assert "Benutzername oder Passwort ist falsch" in body
        # Still anonymous.
        assert client.get("/").status_code == 302

    def test_password_is_stored_hashed(self, db) -> None:
        User.objects.create_user("hashcheck", password="Geheim!1234")
        stored = User.objects.get(username="hashcheck").password
        # Django's default hasher is PBKDF2; the plaintext must never be stored.
        assert stored.startswith("pbkdf2_sha256$")
        assert "Geheim!1234" not in stored

    def test_relative_next_redirects_after_login(self, client, archivist) -> None:
        response = client.post(
            reverse("login"),
            {"username": "archivar1", "password": "Korrekt!1234", "next": "/"},
        )
        assert response.status_code == 302
        assert response.url == "/"

    def test_external_next_is_not_followed(self, client, archivist) -> None:
        """Open redirect guard (OP-03): an external next URL is ignored and
        the user lands on the home page instead."""
        response = client.post(
            reverse("login"),
            {"username": "archivar1", "password": "Korrekt!1234", "next": "https://evil.example/steal"},
        )
        assert response.status_code == 302
        assert response.url == "/"

    def test_logout_returns_to_login_and_clears_session(self, client, archivist) -> None:
        client.force_login(archivist)
        response = client.post(reverse("logout"))
        assert response.status_code == 302
        assert response.url == reverse("login")
        assert client.get("/").status_code == 302


@pytest.mark.django_db
class TestCSRF:
    @pytest.fixture()
    def csrf_client(self):
        """A client that enforces CSRF (default test client disables it)."""
        from django.test import Client

        return Client(enforce_csrf_checks=True)

    def test_login_without_csrf_token_is_rejected(self, csrf_client, archivist) -> None:
        response = csrf_client.post(
            reverse("login"),
            {"username": "archivar1", "password": "Korrekt!1234"},
        )
        assert response.status_code == 403
        # A rejected login must not authenticate the session.
        assert csrf_client.get("/").status_code == 302

    def test_login_with_csrf_token_succeeds(self, csrf_client, archivist) -> None:
        """A token rendered by the form is accepted (the middleware's happy
        path works end to end)."""
        import re

        page = csrf_client.get(reverse("login"))
        match = re.search(
            r'name="csrfmiddlewaretoken" value="([^"]+)"',
            page.content.decode("utf-8"),
        )
        assert match, "CSRF token not rendered in the login form"
        response = csrf_client.post(
            reverse("login"),
            {
                "username": "archivar1",
                "password": "Korrekt!1234",
                "csrfmiddlewaretoken": match.group(1),
            },
        )
        assert response.status_code == 302
        assert response.url == "/"
        assert csrf_client.get("/").status_code == 200

    def test_logout_requires_csrf_token(self, csrf_client, archivist) -> None:
        csrf_client.force_login(archivist)
        response = csrf_client.post(reverse("logout"))
        assert response.status_code == 403
        # A rejected logout must not destroy the session.
        assert csrf_client.get("/").status_code == 200


@pytest.mark.django_db
class TestRateLimiting:
    def test_login_throttles_after_repeated_failures(self, client, archivist) -> None:
        for _ in range(services.MAX_FAILURES):
            client.post(reverse("login"), {"username": "archivar1", "password": "falsch"})
        assert services.login_throttled("archivar1", "127.0.0.1")
        response = client.post(
            reverse("login"),
            {"username": "archivar1", "password": "Korrekt!1234"},
        )
        assert response.status_code == 200
        assert "Zu viele fehlgeschlagene Anmeldeversuche" in response.content.decode("utf-8")
        # Even the correct password is rejected while throttled.
        assert client.get("/").status_code == 302

    def test_successful_login_clears_recent_failures(self, client, archivist) -> None:
        for _ in range(3):
            client.post(reverse("login"), {"username": "archivar1", "password": "falsch"})
        assert services.login_throttled("archivar1", "127.0.0.1") is False
        client.post(reverse("login"), {"username": "archivar1", "password": "Korrekt!1234"})
        assert services.login_throttled("archivar1", "127.0.0.1") is False
        assert services.LoginAttempt.objects.count() == 0

    def test_old_failures_do_not_count(self, client, archivist, db) -> None:
        now = timezone.now()
        services.LoginAttempt.objects.create(
            username="archivar1",
            ip="127.0.0.1",
            success=False,
            created_at=now - timedelta(minutes=30),
        )
        assert services.login_throttled("archivar1", "127.0.0.1") is False

    def test_throttling_is_per_username_and_ip(self, client, archivist) -> None:
        for _ in range(services.MAX_FAILURES):
            services.record_login_failure("archivar1", "127.0.0.1")
        assert services.login_throttled("archivar1", "127.0.0.1") is True
        assert services.login_throttled("other-user", "127.0.0.1") is False
        assert services.login_throttled("archivar1", "10.0.0.9") is False

    def test_username_is_case_insensitive_for_limiting(self, client, archivist) -> None:
        for _ in range(services.MAX_FAILURES):
            services.record_login_failure("ARCHIVAR1", "127.0.0.1")
        assert services.login_throttled("archivar1", "127.0.0.1") is True


class TestCookieSecurityContract:
    """OP-03: secure cookies are enforced by the deployment (nas) profile and
    never by a runtime toggle. This test session runs the local profile
    (plain HTTP on loopback), so the secure-cookie flags are off here while
    the always-on protections (HTTPOnly, nosniff, DENY, host validation)
    remain active — the production flags are driven by the same
    profile-derived expression in settings.py."""

    def test_local_session_keeps_http_only_and_host_validation(self) -> None:
        from django.conf import settings

        assert settings.SESSION_COOKIE_HTTPONLY is True
        assert settings.SECURE_CONTENT_TYPE_NOSNIFF is True
        assert settings.X_FRAME_OPTIONS == "DENY"
        assert settings.LOGIN_URL == "login"
        assert settings.ALLOWED_HOSTS  # host validation active (WP-02 tested)

    def test_local_session_secure_cookie_flags_off(self) -> None:
        """Local profile is loopback HTTP, so Secure/SSL-redirect flags are
        off; they are automatically on in the nas profile (profile-derived)."""
        from django.conf import settings

        from config.env import env

        assert env.profile == "local"
        assert env.secure_transport_required is False
        assert settings.SECURE_SSL_REDIRECT is False
        assert settings.SESSION_COOKIE_SECURE is False
        assert settings.CSRF_COOKIE_SECURE is False

    def test_nas_profile_env_selects_secure_flags(self, tmp_path) -> None:
        """The flag derivation is profile-driven: a parsed nas environment sets
        secure_transport_required, which settings.py uses to turn the
        secure-cookie and SSL-redirect flags on in production."""
        from config.env import parse_env

        secret = tmp_path / "key"
        secret.write_text("k\n", encoding="utf-8")
        env = parse_env(
            {
                "DJANGO_SECRET_KEY_FILE": str(secret),
                "APP_ALLOWED_HOSTS": "notenarchiv.example.invalid",
                "DATABASE_PATH": "/data/db.sqlite3",
                "SOURCE_DIR": "/a",
                "CURATED_DIR": "/b",
                "PROCESSED_DIR": "/c",
                "STATUS_DIR": "/d",
                "EXPORT_DIR": "/e",
            }
        )
        assert env.profile == "nas"
        assert env.secure_transport_required is True
