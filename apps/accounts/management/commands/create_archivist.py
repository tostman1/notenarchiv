"""Provision authenticated archivist accounts (WP-03, UI-01).

Interactive command for controlled account management:

    python manage.py create_archivist
    python manage.py create_archivist --username max --random-password
    python manage.py create_archivist --username max --set-password

All accounts have identical functional rights (UI-01: no role model).
Passwords are hashed with Django's default (PBKDF2) hasher; the secret
never appears in logs. Credentials must never be placed in Compose or the
repository (ARCHITECTURE.md: bootstrap interactively or via protected
provisioning).
"""

from __future__ import annotations

import getpass

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.utils.crypto import get_random_string

_USERNAME_VALIDATOR = UnicodeUsernameValidator()


class Command(BaseCommand):
    help = "Create or update the password of an archivist account."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--username", help="Account username (default: interactive prompt).")
        parser.add_argument("--random-password", action="store_true", help="Generate and print a random password once.")
        parser.add_argument("--set-password", action="store_true", help="Update the password of an existing account.")

    def handle(self, *args, **options) -> None:
        User = get_user_model()
        username = (options["username"] or input("Benutzername: ")).strip()
        try:
            _USERNAME_VALIDATOR(username)
        except ValidationError as exc:
            raise CommandError(f"invalid username {username!r}: {'; '.join(exc.messages)}") from exc

        exists = User.objects.filter(username=username).exists()
        if exists and not options["set_password"]:
            raise CommandError(f"account {username!r} already exists; use --set-password to change its password")
        if not exists and options["set_password"]:
            raise CommandError(f"account {username!r} does not exist; create it without --set-password")

        if options["random_password"]:
            password = get_random_string(20, allowed_chars="abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789")
        else:
            password = getpass.getpass("Passwort: ")
        validate_password(password)

        user = User.objects.filter(username=username).first()
        if user is None:
            user = User(username=username)
        user.set_password(password)
        user.save()

        self.stdout.write(self.style.SUCCESS(f"account '{username}' saved (password hashed)"))
        if options["random_password"]:
            self.stdout.write(f"random password (shown once): {password}")
