"""Login forms (UI-04/UI-02: German labels, controlled fields only)."""

from __future__ import annotations

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _


class GermanAuthenticationForm(AuthenticationForm):
    """AuthenticationForm with German field labels and error text."""

    username = forms.CharField(label=_("Benutzername"), max_length=150, strip=False)
    password = forms.CharField(
        label=_("Passwort"),
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )

    error_messages = {
        **AuthenticationForm.error_messages,
        "invalid_login": _("Benutzername oder Passwort ist falsch."),
        "inactive": _("Dieses Konto ist nicht aktiv."),
    }


def create_archivist(username: str, password: str) -> User:
    """Create an authenticated archivist account (UI-01: identical rights).

    All business pages are open to any authenticated user; no role model is
    needed. The caller owns credential sourcing (interactive provisioning
    command, see apps.accounts.management).
    """
    user = User.objects.create_user(username=username, password=password)
    return user
