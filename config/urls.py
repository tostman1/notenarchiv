"""Root URL configuration.

Only the public, non-sensitive endpoints exist in the WP-02 skeleton:
``/healthz`` (unauthenticated, loopback-friendly host handling) and
``/`` (business root, login-protected from WP-03 onward). Business routes
of the domain apps are added as their packages land.
"""

from __future__ import annotations

from django.http import JsonResponse
from django.urls import path

from apps.accounts import views as account_views


def healthz(_request) -> JsonResponse:
    """Minimal liveness probe.

    Kept dependency-free and side-effect free: it must not open a database
    connection, because Compose healthchecks run before and independently
    of migration state during startup windows.
    """
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("healthz", healthz, name="healthz"),
    path("", account_views.home_view, name="home"),
    path("login/", account_views.login_view, name="login"),
    path("logout/", account_views.logout_view, name="logout"),
]
