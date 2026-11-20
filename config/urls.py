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
from apps.catalog import views as catalog_views
from apps.jobs import job_views as job_management
from apps.jobs import views as job_views


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
    path("jobs/", job_management.job_list, name="job_list"),
    path("jobs/<uuid:job_id>/", job_management.job_detail, name="job_detail"),
    path("jobs/<uuid:job_id>/cancel/", job_management.job_cancel, name="job_cancel"),
    path("catalog/<slug:entity>/", catalog_views.record_list, name="catalog_list"),
    path("catalog/<slug:entity>/new/", catalog_views.record_edit, name="catalog_create"),
    path("catalog/<slug:entity>/<uuid:record_id>/", catalog_views.record_detail, name="catalog_detail"),
    path("catalog/<slug:entity>/<uuid:record_id>/edit/", catalog_views.record_edit, name="catalog_edit"),
    path("catalog/<slug:entity>/<uuid:record_id>/delete/", catalog_views.record_delete, name="catalog_delete"),
    path(
        "catalog/arrangements/<uuid:record_id>/apply-template/",
        catalog_views.template_apply,
        name="catalog_apply_template",
    ),
    path("diagnostics/", job_views.debug_logs, name="debug_logs"),
    path("diagnostics/records/", job_views.debug_logs, {"output": "records"}, name="debug_records"),
    path("diagnostics/download/", job_views.debug_logs, {"output": "download"}, name="debug_download"),
]
