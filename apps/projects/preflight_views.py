"""Authenticated current full/excerpt preflight and immutable authorization."""

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, render
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from apps.projects.models import Project
from apps.projects.preflight_forms import PreflightAcknowledgement, PreflightSelection
from apps.projects.preflight_services import build_report, validate_acknowledgement


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def preflight(request, project_id, kind="FULL"):
    project = get_object_or_404(Project, pk=project_id)
    selection = PreflightSelection(request.POST if request.method == "POST" else None, project=project)
    context = {"project": project, "selection": selection, "excerpt": kind == "EXCERPT"}
    status = 200
    if request.method == "POST" and selection.is_valid():
        try:
            report = build_report(
                project.pk,
                participant_ids=selection.cleaned_data["participants"],
                position_ids=selection.cleaned_data["positions"],
            )
            context["report"] = report
            context["pending_count"] = len(report.payload["pending"])
            context["ack_form"] = PreflightAcknowledgement(report=report, actor=request.user)
            context["full_scope"] = set(report.session.positions) == set(
                project.positions.filter(active=True).values_list("pk", flat=True)
            )
            if request.POST.get("action") == "acknowledge":
                form = PreflightAcknowledgement(request.POST, report=report, actor=request.user)
                context["ack_form"] = form
                if not form.is_valid():
                    status = 400
                else:
                    validate_acknowledgement(
                        report, form.cleaned_data["token"], form.cleaned_data["acknowledgements"], request.user
                    )
                    context["acknowledged"] = True
            elif request.POST.get("action") == "authorize":
                from apps.exports.snapshot_services import authorize

                form = PreflightAcknowledgement(request.POST, report=report, actor=request.user)
                context["ack_form"] = form
                if not form.is_valid():
                    status = 400
                else:
                    run = authorize(
                        project.pk,
                        participant_ids=selection.cleaned_data["participants"],
                        position_ids=selection.cleaned_data["positions"],
                        token=form.cleaned_data["token"],
                        acknowledgements=form.cleaned_data["acknowledgements"],
                        actor=request.user,
                        kind=kind,
                    )
                    context["authorized_run"] = run
        except ValidationError as exc:
            context["error"] = " ".join(exc.messages)
            status = 409
        except OSError:
            context["error"] = _("Prüfspeicher oder PDF-Prüfung nicht verfügbar; erneut versuchen.")
            status = 409
    elif request.method == "POST":
        status = 400
    return render(request, "projects/preflight.html", context, status=status)
