"""HTTP contract tests: public health endpoint and sanitized error pages."""

from __future__ import annotations

import pytest


@pytest.mark.django_db
class TestHealthz:
    def test_healthz_is_public_and_reports_ok(self, client) -> None:
        """The liveness probe is unauthenticated and returns a minimal 200.
        It must not depend on business routes or the database."""
        response = client.get("/healthz")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        assert "application/json" in response["Content-Type"]

    def test_healthz_accepts_loopback_host(self, client) -> None:
        response = client.get("/healthz", HTTP_HOST="127.0.0.1")
        assert response.status_code == 200


class TestErrorResponseSanitization:
    @pytest.fixture()
    def failing_client(self, django_test_environment):
        """A client whose view raises, to prove no traceback leaks (GR-13 /
        OP-03: no user-facing production tracebacks, even in the local
        profile). ``raise_request_exception=False`` returns the sanitized
        500 response instead of propagating the exception."""
        from django.test import Client
        from django.test.utils import override_settings

        with override_settings(
            ROOT_URLCONF="tests.test_error_urls",
            ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
        ):
            yield Client(raise_request_exception=False)

    def test_server_error_is_sanitized(self, failing_client) -> None:
        response = failing_client.get("/boom")
        assert response.status_code == 500
        body = response.content.decode("utf-8", errors="replace")
        assert "Traceback" not in body
        assert "intentional test failure" not in body

    def test_bad_host_is_rejected(self, client) -> None:
        """Host validation stays active: an arbitrary Host header is refused."""
        response = client.get("/healthz", HTTP_HOST="evil.example")
        assert response.status_code == 400
