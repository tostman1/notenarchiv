"""Thin read-only preview endpoints; errors never contain paths/parser output."""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_POST

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
        except (Http404, FileError, PdfError, OSError, ValueError, ValidationError):
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


def _sequence_ids(request):
    values = request.GET.getlist("region")
    if len(values) > 16 or any(len(value) > 36 for value in values):
        raise Http404
    return [value for value in values if value]


@protected_preview
def region_sequence_viewer(request, file):
    from urllib.parse import urlencode
    from uuid import UUID

    from apps.archive.models import PageRegionRevision

    values = _sequence_ids(request)
    try:
        identifiers = [UUID(value) for value in values]
    except ValueError:
        raise Http404 from None
    if not identifiers or file.kind != "BASE":
        raise Http404
    found = PageRegionRevision.objects.filter(
        pk__in=identifiers,
        region__source_page__source_version_id=file.source_version_id,
    ).count()
    if found != len(set(identifiers)):
        raise Http404
    document_url = reverse("archive_preview:region_sequence_document", args=[file.pk])
    return render(
        request,
        "archive/region_sequence_preview.html",
        {
            "file": file,
            "export_document_url": document_url + "?" + urlencode([("region", value) for value in values]),
            "sequence_count": len(values),
        },
    )


@protected_preview
def content_proposal_viewer(request, file, revision_id):
    from apps.archive.content_preview_services import proposal_context
    from apps.archive.content_review_forms import ContentInspectionForm

    revision, identifiers = proposal_context(file, revision_id)
    return render(
        request,
        "archive/content_proposal_preview.html",
        {
            "file": file,
            "proposal": revision,
            "sequence_count": len(identifiers),
            "inspection_form": ContentInspectionForm(initial={"fingerprint": revision.fingerprint}),
            "export_document_url": reverse("archive_preview:content_proposal_document", args=[file.pk, revision.pk]),
        },
    )


@login_required
@require_POST
def content_proposal_inspect(request, file_id, revision_id):
    from django.contrib import messages

    from apps.archive.content_preview_services import proposal_context
    from apps.archive.content_review_forms import ContentInspectionForm
    from apps.archive.content_services import inspect_content

    form = ContentInspectionForm(request.POST)
    try:
        file = services.preview_file(file_id)
        revision, identifiers = proposal_context(file, revision_id)
        if not form.is_valid():
            raise ValidationError("Explicit inspection attestation is required.")
        inspect_content(
            revision.pk,
            actor=request.user,
            expected_fingerprint=form.cleaned_data["fingerprint"],
            visually_reviewed=form.cleaned_data["visually_reviewed"],
        )
    except (Http404, FileError, PdfError, OSError, ValueError, ValidationError):
        messages.error(
            request, _("Sichtprüfung nicht gespeichert. Quelle, Revision und ausdrückliche Bestätigung prüfen.")
        )
    else:
        messages.success(
            request, _("Sichtprüfung dieser Inhaltsrevision gespeichert; noch keine musikalische Freigabe.")
        )
    response = redirect("archive_preview:content_proposal_viewer", file_id=file_id, revision_id=revision_id)
    response["Cache-Control"] = "private, no-store"
    return response


@protected_preview
def content_proposal_document(request, file, revision_id):
    from apps.archive.content_preview_services import proposal_preview

    response = HttpResponse(proposal_preview(file, revision_id), content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="unconfirmed-content-inspection.pdf"'
    response["Content-Security-Policy"] = "sandbox; default-src 'none'"
    return response


@protected_preview
def region_sequence_document(request, file):
    output = services.region_sequence(file, _sequence_ids(request))
    response = HttpResponse(output, content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="unconfirmed-inspection-preview.pdf"'
    response["Content-Security-Policy"] = "sandbox; default-src 'none'"
    return response
