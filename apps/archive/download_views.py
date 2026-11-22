"""Authenticated direct notes and bounded ZIP; errors contain no private paths."""

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import FileResponse, HttpResponse
from django.shortcuts import render
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST

from apps.archive import download_services as service
from apps.archive import library_services
from core.files import FileError


def error_response(*, conflict=False):
    return HttpResponse(
        _("Auswahl geändert oder abgelaufen. Bitte neu auswählen.")
        if conflict
        else _("Download nicht verfügbar. Nur bestätigte, unveränderte Ausgaben wählen; maximal 20 PDFs und 512 MiB."),
        status=409 if conflict else 400,
        content_type="text/plain",
    )


def attachment(selected, *, zipped):
    stream = service.stage(selected, zipped=zipped)
    try:
        response = FileResponse(
            stream,
            as_attachment=True,
            filename="archivnoten.zip" if zipped else f"note-{selected[0].pk}.pdf",
            content_type="application/zip" if zipped else "application/pdf",
        )
        response["Content-Security-Policy"] = "sandbox; default-src 'none'"
        response["X-Content-Type-Options"] = "nosniff"
        response["Cross-Origin-Resource-Policy"] = "same-origin"
        return response
    except BaseException:
        stream.close()
        raise


@never_cache
@login_required
@require_GET
def note(request, file_id):
    try:
        return attachment(service.files([file_id]), zipped=False)
    except service.SelectionChanged:
        return error_response(conflict=True)
    except (ValidationError, FileError, OSError, ValueError):
        return error_response()


@never_cache
@login_required
@require_POST
def selection(request):
    try:
        selected = service.files(request.POST.getlist("file"))
        if any(not library_services.verify_file(file) for file in selected):
            raise ValidationError("Selected bytes unavailable.")
        return render(
            request,
            "archive/download_selection.html",
            {
                "files": selected,
                "token": service.selection_token(selected, request.user),
                "total": sum(file.byte_size for file in selected),
            },
        )
    except (ValidationError, FileError, OSError, ValueError):
        return error_response()


@never_cache
@login_required
@require_POST
def download_selection(request):
    try:
        selected = service.from_token(request.POST.get("token"), request.user)
        return attachment(selected, zipped=len(selected) > 1)
    except service.SelectionChanged:
        return error_response(conflict=True)
    except (ValidationError, FileError, OSError, ValueError):
        return error_response()
