"""Authenticated, mode-gated diagnostic routes (WP-04b)."""

import json
from functools import wraps

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from apps.jobs.forms import DiagnosticFilters
from apps.jobs.services.diagnostics import InvalidCursor, read_page


def diagnostics_only(view):
    @wraps(view)
    def gated(request, *args, **kwargs):
        if not settings.DEBUG_MODE:
            raise Http404
        return view(request, *args, **kwargs)

    return gated


@never_cache
@diagnostics_only
@login_required
@require_GET
def debug_logs(request, output="page"):
    params = request.GET.copy()
    params.setdefault("source", "web")
    form = DiagnosticFilters(params)
    if not form.is_valid():
        if output == "page":
            return render(request, "jobs/debug_logs.html", {"form": form, "page": {}}, status=400)
        return JsonResponse({"error": _("Ungültige Filter.")}, status=400)
    try:
        options = {"budget": 1024 * 1024, "limit": 1000} if output == "download" else {}
        page = read_page(settings.DIAGNOSTIC_LOG_DIR, form.cleaned_data, params.get("cursor", ""), **options)
    except InvalidCursor:
        return JsonResponse({"error": _("Die Leseposition ist ungültig oder abgelaufen. Bitte neu laden.")}, status=400)
    except OSError:
        return JsonResponse({"error": _("Die Diagnosemeldungen sind derzeit nicht verfügbar.")}, status=503)
    if output == "records":
        return JsonResponse(page)
    if output == "download":
        body = "".join(json.dumps(record) + "\n" for record in page["records"])
        response = HttpResponse(body, content_type="application/x-ndjson")
        response["Content-Disposition"] = f'attachment; filename="diagnostics-{form.cleaned_data["source"]}.jsonl"'
        response["X-Next-Cursor"] = page["cursor"]
        response["X-Log-More"] = str(page["more"]).lower()
        return response
    download_query = params.urlencode()
    params.pop("cursor", None)
    filters_query = params.urlencode()
    params["cursor"] = page["cursor"]
    return render(
        request,
        "jobs/debug_logs.html",
        {
            "form": form,
            "page": page,
            "filters_query": filters_query,
            "download_query": download_query,
            "next_query": params.urlencode(),
        },
    )
