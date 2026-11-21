"""Thin authenticated review UI; GET/preview never changes workflow state."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from apps.archive import models as m
from apps.archive import review_forms as forms
from apps.archive import review_services as services
from apps.archive.index_presentation import CANDIDATES, REVIEW
from apps.jobs.models import Job
from apps.jobs.presentation import describe

FORMS = {
    "save": forms.CorrectionForm,
    "inspect": forms.InspectionForm,
    "approve": forms.ApprovalForm,
    "reject": forms.RejectionForm,
}


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def detail(request, file_id):
    try:
        file = services.review_file(file_id)
    except m.ArchiveFile.DoesNotExist:
        raise Http404 from None
    failed_form, status = None, 200
    if request.method == "POST":
        action = request.POST.get("action")
        if action not in FORMS:
            raise Http404
        failed_form = FORMS[action](request.POST)
        if failed_form.is_valid():
            try:
                result = services.act(file, action, failed_form.cleaned_data, request.user)
            except (ValidationError, ValueError, OSError, Http404):
                failed_form.add_error(
                    None,
                    _(
                        "Prüfstand oder Dateistatus ungültig. Neu laden, Zuordnung speichern "
                        "und diese Version erneut prüfen."
                    ),
                )
                status = 409
            else:
                text = {
                    "save": _("Zuordnung gespeichert. Diese neue Zuordnung muss visuell geprüft werden."),
                    "inspect": _("Ihre ausdrückliche visuelle Prüfung ist für diese Version gespeichert."),
                    "approve": _("Freigabe beauftragt. Nutzbar erst nach erfolgreicher, verifizierter Publikation."),
                    "reject": _("Vorschlag verworfen. Datei und Prüfgeschichte bleiben erhalten."),
                }
                messages.success(request, text[action])
                if isinstance(result, Job):
                    return redirect("job_detail", job_id=result.pk)
                return redirect("archive_review_detail", file_id=file.pk)
        else:
            status = 400
        file = services.review_file(file.pk)
    proposal = file.current_proposal
    initial = {
        "expected_revision": file.revision,
        "source_version": file.source_version_id,
        "sha256": file.sha256,
        "proposal": file.current_proposal_id,
    }
    if proposal:
        parts = list(proposal.parts.select_related("part__instrument"))
        initial.update(
            arrangement=proposal.arrangement_id,
            parts=[entry.part_id for entry in parts],
            instruments=list({entry.part.instrument_id for entry in parts}),
        )
    else:
        parts = []
    candidates = list(
        file.candidates.select_related("proposed_arrangement__work", "proposed_work")
        .prefetch_related("parts__part__instrument")
        .order_by("-created_at")[:10]
    )
    inspected = bool(
        proposal
        and proposal.inspections.filter(
            reviewer=request.user, inspected_sha256=file.sha256, explicit_attestation=True
        ).exists()
    )
    jobs = [describe(operation.job) for operation in file.operations.select_related("job").order_by("-created_at")[:10]]
    file.review_label = REVIEW.get(
        file.review_state, _("Bestätigt") if file.review_state == "CONFIRMED" else _("Zurückgezogen")
    )
    file.candidate_label = CANDIDATES[file.candidate_state]
    response = render(
        request,
        "archive/review_detail.html",
        {
            "file": file,
            "proposal": proposal,
            "parts": parts,
            "candidates": candidates,
            "inspected": inspected,
            "jobs": jobs,
            "failed_form": failed_form,
            "correction": forms.CorrectionForm(initial=initial),
            "inspection": forms.InspectionForm(initial=initial),
            "approval": forms.ApprovalForm(initial=initial),
            "rejection": forms.RejectionForm(initial=initial),
            "audit": file.auditevent_set.select_related("actor").order_by("-created_at")[:25],
        },
        status=status,
    )
    response["Content-Security-Policy"] = (
        "default-src 'none'; script-src 'self'; worker-src 'self'; connect-src 'self'; "
        "style-src 'self'; img-src 'self' blob: data:; font-src 'self' blob:; object-src 'none'; base-uri 'none'; "
        "form-action 'self'; frame-ancestors 'none'"
    )
    return response
