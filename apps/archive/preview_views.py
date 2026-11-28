"""Thin read-only preview endpoints; errors never contain paths/parser output."""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET

from apps.archive import preview_services as services
from core.files import FileError
from core.pdf.types import PdfError


def protected_preview(view):
    @login_required
    @require_GET
    @wraps(view)
    def endpoint(request, file_id, **kwargs):
        try:
            file = services.preview_file(file_id)
            response = view(request, file, **kwargs)
        except (Http404, FileError, PdfError, OSError, ValueError):
            response = HttpResponse(_("Die PDF-Vorschau ist nicht verfügbar."), status=404, content_type="text/plain")
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        response["Referrer-Policy"] = "same-origin"
        response["Cross-Origin-Resource-Policy"] = "same-origin"
        response.setdefault(
            "Content-Security-Policy",
            (
                "default-src 'none'; script-src 'self'; worker-src 'self'; "
                "connect-src 'self'; style-src 'self'; img-src 'self' blob: data:; "
                "font-src 'self' blob:; object-src 'none'; base-uri 'none'; "
                "form-action 'self'; frame-ancestors 'none'"
            ),
        )
        return response

    return endpoint


@protected_preview
def viewer(request, file):
    return render(request, "archive/preview.html", {"file": file})


@protected_preview
def document(request, file):
    response = HttpResponse(services.preview_bytes(file), content_type="application/pdf")
    # Never hand original active PDF content to a browser plugin inline. The
    # custom PDF.js canvas viewer fetches it as bytes and exposes no actions.
    response["Content-Disposition"] = f'attachment; filename="preview-{file.pk}.pdf"'
    response["Content-Security-Policy"] = "sandbox; default-src 'none'"
    return response


@protected_preview
def thumbnail(request, file, page):
    return HttpResponse(services.thumbnail(file, page), content_type="image/png")


@protected_preview
def ocr_excerpt(request, file, evidence_id):
    return HttpResponse(services.ocr_excerpt(file, evidence_id), content_type="image/png")


@protected_preview
def region_excerpt(request, file, revision_id):
    return HttpResponse(services.region_excerpt(file, revision_id), content_type="image/png")
