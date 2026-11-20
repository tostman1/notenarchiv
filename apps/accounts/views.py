"""Authentication views (WP-03).

German UI (UI-02). All business views require authentication (OP-03);
login and logout are the only public entry points. Login is rate-limited
per (username, client IP) pair before any password check is performed.
"""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from apps.accounts.forms import GermanAuthenticationForm
from apps.accounts.services import login_throttled, record_login_failure, record_login_success


def _client_ip(request: HttpRequest) -> str:
    """Client IP from the direct connection.

    Behind the reverse proxy the leftmost X-Forwarded-For entry is the
    originating client; the proxy is trusted because it is the only inbound
    path (ARCHITECTURE.md: never trust arbitrary forwarded headers from
    untrusted clients — only the first entry, and only when present).
    """
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def login_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect(reverse("home"))
    if request.method == "POST":
        form = GermanAuthenticationForm(request, data=request.POST)
        username = (request.POST.get("username") or "").strip()
        if login_throttled(username, _client_ip(request)):
            form.add_error(None, "Zu viele fehlgeschlagene Anmeldeversuche. Bitte warten Sie einige Minuten.")
            return render(request, "accounts/login.html", {"form": form})
        if form.is_valid():
            record_login_success(username, _client_ip(request))
            login(request, form.get_user())
            return redirect(_safe_next(request))
        record_login_failure(username, _client_ip(request))
    else:
        form = GermanAuthenticationForm()
    return render(request, "accounts/login.html", {"form": form, "next": request.GET.get("next", "")})


def _safe_next(request: HttpRequest) -> str:
    """Return a safe post-login destination, guarding against open redirect.

    Only relative paths or URLs on the allowed hosts are accepted; anything
    else falls back to the home page (OP-03).
    """
    next_url = request.GET.get("next") or request.POST.get("next") or ""
    if url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return next_url
    return reverse("home")


def logout_view(request: HttpRequest) -> HttpResponse:
    logout(request)
    messages.info(request, "Sie wurden abgemeldet.")
    return redirect(reverse("login"))


@login_required
def home_view(request: HttpRequest) -> HttpResponse:
    """Business root (UI-02 Übersicht placeholder; real dashboard later)."""
    return render(request, "home.html")
