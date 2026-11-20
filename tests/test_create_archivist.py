"""create_archivist command tests (WP-03, UI-01)."""

from __future__ import annotations

from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError

User = get_user_model()


@pytest.mark.django_db
class TestCreateArchivist:
    def test_random_password_creates_hashed_account(self) -> None:
        out = StringIO()
        call_command("create_archivist", username="archivar1", random_password=True, stdout=out)
        user = User.objects.get(username="archivar1")
        assert user.password.startswith("pbkdf2_sha256$")
        output = out.getvalue()
        assert "random password (shown once):" in output
        generated = output.split("random password (shown once):")[1].strip()
        assert user.check_password(generated)

    def test_duplicate_creation_is_rejected(self) -> None:
        out = StringIO()
        call_command("create_archivist", username="archivar1", random_password=True, stdout=out)
        with pytest.raises(CommandError, match="already exists"):
            call_command("create_archivist", username="archivar1", random_password=True, stdout=StringIO())

    def test_set_password_requires_existing_account(self) -> None:
        with pytest.raises(CommandError, match="does not exist"):
            call_command("create_archivist", username="ghost", random_password=True, set_password=True)

    def test_set_password_updates_existing_account(self) -> None:
        out = StringIO()
        call_command("create_archivist", username="archivar1", random_password=True, stdout=out)
        out2 = StringIO()
        call_command("create_archivist", username="archivar1", random_password=True, set_password=True, stdout=out2)
        user = User.objects.get(username="archivar1")
        generated = out2.getvalue().split("random password (shown once):")[1].strip()
        assert user.check_password(generated)

    def test_invalid_username_is_rejected(self) -> None:
        with pytest.raises(CommandError, match="invalid username"):
            call_command("create_archivist", username="bad username!", random_password=True)

    def test_weak_password_is_rejected(self, monkeypatch) -> None:
        """A password failing validation is rejected before any account is
        written (the CLI takes no --password argument, so the interactive
        getpass is patched for the test)."""
        import getpass

        from django.core.exceptions import ValidationError

        monkeypatch.setattr(getpass, "getpass", lambda _prompt: "abc123")
        out = StringIO()
        with pytest.raises(ValidationError):
            call_command("create_archivist", username="archivar1", stdout=out)
        assert not User.objects.filter(username="archivar1").exists()
