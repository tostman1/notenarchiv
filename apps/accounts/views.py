"""Authentication views (WP-03).

German UI (UI-02). All business views require authentication (OP-03);
login and logout are the only public entry points. Login is rate-limited
per (username, client IP) pair before any password check is performed.
"""

from __future__ import annotations

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from apps.accounts.forms import GermanAuthenticationForm
from apps.accounts.services import login_throttled, record_login_failure, record_login_success


def login_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect(reverse("home"))
    destination = _safe_next(request)
    if request.method == "POST":
        peer = request.META["REMOTE_ADDR"]
        username = (request.POST.get("username") or "").strip()
        if login_throttled(username, peer):
            messages.error(request, _("Zu viele fehlgeschlagene Anmeldeversuche. Bitte warten Sie einige Minuten."))
            form = GermanAuthenticationForm(initial={"username": username})
            return render(request, "accounts/login.html", {"form": form, "next": destination})
        form = GermanAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            record_login_success(username, peer)
            login(request, form.get_user())
            return redirect(destination)
        record_login_failure(username, peer)
    else:
        form = GermanAuthenticationForm()
    return render(request, "accounts/login.html", {"form": form, "next": destination})


def _safe_next(request: HttpRequest) -> str:
    """Return a safe post-login destination, guarding against open redirect.

    Only relative paths or URLs on the allowed hosts are accepted; anything
    else falls back to the home page (OP-03).
    """
    next_url = request.GET.get("next") or request.POST.get("next") or ""
    if url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return next_url
    return reverse("home")


@require_POST
def logout_view(request: HttpRequest) -> HttpResponse:
    logout(request)
    messages.info(request, _("Sie wurden abgemeldet."))
    return redirect(reverse("login"))


@login_required
def home_view(request: HttpRequest) -> HttpResponse:
    """Business root (UI-02 Übersicht placeholder; real dashboard later)."""
    return render(request, "home.html", {"diagnostics_enabled": settings.DEBUG_MODE})
