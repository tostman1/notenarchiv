"""Thin authenticated review UI; GET/preview never changes workflow state."""

from contextlib import suppress

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import DatabaseError
from django.db.models import OuterRef, Q, Subquery
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from apps.archive import models as m
from apps.archive import review_forms as forms
from apps.archive import review_services as services
from apps.archive.index_presentation import CANDIDATES, REVIEW, review_files
from apps.archive.review_presentation import EVENTS, REASONS
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
        if action == "region_save":
            from apps.archive.region_editor_services import save_rectangle

            selection_form = forms.OcrSelectionForm(request.POST)
            revision_form = forms.RegionRevisionForm(request.POST)
            try:
                if not selection_form.is_valid() or not revision_form.is_valid():
                    raise ValidationError("Invalid region edit.")
                values = selection_form.cleaned_data
                save_rectangle(
                    file.pk,
                    selection={
                        "page": values["page"] - 1,
                        "box": [values[name] / 100 for name in ("left", "top", "right", "bottom")],
                    },
                    **revision_form.cleaned_data,
                )
            except (ValidationError, DatabaseError, ValueError, OSError, Http404):
                messages.error(request, _("Bereich nicht gespeichert. Quellstand und Grenzen prüfen; neu laden."))
            else:
                messages.success(request, _("Bereichsversion gespeichert – keine Zuordnung, Inspektion oder Freigabe."))
            return redirect("archive_review_detail", file_id=file.pk)
        if action in ("ocr", "ocr_selection"):
            from apps.archive.ocr_services import request as request_ocr

            try:
                selection = None
                if action == "ocr_selection":
                    selection_form = forms.OcrSelectionForm(request.POST)
                    if not selection_form.is_valid():
                        raise ValidationError("Invalid OCR selection.")
                    values = selection_form.cleaned_data
                    selection = {
                        "page": values["page"] - 1,
                        "box": [values[name] / 100 for name in ("left", "top", "right", "bottom")],
                    }
                job = request_ocr(file.pk, selection=selection)
            except (ValidationError, DatabaseError, ValueError, Http404):
                messages.error(
                    request, _("OCR-Auftrag nicht möglich. Dateistatus prüfen und bewusst erneut versuchen.")
                )
                return redirect("archive_review_detail", file_id=file.pk)
            return redirect("job_detail", job_id=job.pk)
        if action not in FORMS:
            raise Http404
        failed_form = FORMS[action](request.POST, auto_id=action + "_%s")
        if failed_form.is_valid():
            try:
                result = services.act(file, action, failed_form.cleaned_data, request.user)
            except DatabaseError:
                failed_form.add_error(
                    None, _("Datenbank momentan belegt. Prüfseite neu laden und den Auftrag bewusst erneut versuchen.")
                )
                status = 409
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
    from core.page_geometry import DisplayTransform, PageGeometry

    latest_region = m.PageRegionRevision.objects.filter(region_id=OuterRef("region_id")).order_by("-number")
    regions = list(
        m.PageRegionRevision.objects.filter(
            region__source_page__source_version_id=file.source_version_id,
            pk=Subquery(latest_region.values("pk")[:1]),
        )
        .select_related("region__source_page")
        .order_by("region__source_page__page_index", "region_id")[:20]
    )
    for region in regions:
        page = region.region.source_page
        geometry = PageGeometry(page.media_box, page.original_crop_box, page.rotation, page.user_unit)
        transform = DisplayTransform(geometry, 1)
        width, height = geometry.display_points
        left, bottom, right, top = region.bounds_points
        corners = [transform.to_pixels([x, y]) for x in (left, right) for y in (bottom, top)]
        region.display_box = [
            min(p[0] for p in corners) / width * 100,
            min(p[1] for p in corners) / height * 100,
            max(p[0] for p in corners) / width * 100,
            max(p[1] for p in corners) / height * 100,
        ]
        region.page_number = page.page_index + 1
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
    evidence_by_key = {
        evidence.cache_key: evidence
        for evidence in m.OcrPageEvidence.objects.filter(
            source_version_id=file.source_version_id,
            cache_key__in=[candidate.rule_version for candidate in candidates if candidate.method == "OCR"],
        )
    }
    heading_rules = None
    if evidence_by_key:
        from apps.archive.recognition import build_rule_set

        heading_rules = build_rule_set()
    for candidate in candidates:
        candidate.compound_headings = []
        candidate.ocr_evidence = evidence_by_key.get(candidate.rule_version) if candidate.method == "OCR" else None
        if candidate.ocr_evidence:
            candidate.ocr_words = candidate.ocr_evidence.evidence.get("words", [])[:100]
            candidate.source_page_number = candidate.ocr_evidence.page + 1
            if candidate.ocr_evidence.evidence.get("rules") == heading_rules.version:
                from apps.archive.compound_recognition import headings

                # Historical evidence remains readable even if its shape
                # cannot support additional compound observations.
                with suppress(ValueError):
                    candidate.compound_headings = headings(candidate.ocr_evidence.evidence, heading_rules)[:16]
        candidate.reason_labels = [
            REASONS.get(reason, _("Erkennung unsicher; Inhalt und Zuordnung manuell prüfen."))
            for reason in candidate.reasons
        ]
    audit = list(file.auditevent_set.select_related("actor").order_by("-created_at")[:25])
    for event in audit:
        event.event_label = EVENTS.get(event.event, _("Archivstatus aktualisiert"))
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
    queue = review_files().order_by("created_at", "pk")
    previous = queue.filter(Q(created_at__lt=file.created_at) | Q(created_at=file.created_at, pk__lt=file.pk)).last()
    following = queue.filter(Q(created_at__gt=file.created_at) | Q(created_at=file.created_at, pk__gt=file.pk)).first()
    response = render(
        request,
        "archive/review_detail.html",
        {
            "file": file,
            "proposal": proposal,
            "parts": parts,
            "candidates": candidates,
            "ocr_selection": forms.OcrSelectionForm(),
            "region_revision": forms.RegionRevisionForm(
                initial={"expected_file_revision": file.revision, "source_version_id": file.source_version_id}
            ),
            "regions": regions,
            "inspected": inspected,
            "jobs": jobs,
            "failed_form": failed_form,
            "correction": forms.CorrectionForm(initial=initial, auto_id="correction_%s"),
            "inspection": forms.InspectionForm(initial=initial, auto_id="inspection_%s"),
            "approval": forms.ApprovalForm(initial=initial, auto_id="approval_%s"),
            "rejection": forms.RejectionForm(initial=initial, auto_id="rejection_%s"),
            "audit": audit,
            "previous": previous,
            "following": following,
        },
        status=status,
    )
    response["Content-Security-Policy"] = (
        "default-src 'none'; script-src 'self'; worker-src 'self'; connect-src 'self'; "
        "style-src 'self'; img-src 'self' blob: data:; font-src 'self' blob:; object-src 'none'; base-uri 'none'; "
        "form-action 'self'; frame-ancestors 'none'"
    )
    return response
