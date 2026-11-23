"""Authenticated contents/history selection; no project assignment mutations."""

from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods

from apps.exports.models import GenerationRun, GenerationSnapshot
from apps.exports.selection_services import authorize_selection, contents_report, historical_report, selection_token
from apps.projects.models import Project


class HistoricalSelection(forms.Form):
    participants = forms.MultipleChoiceField(label=_("Historische Personen"), widget=forms.CheckboxSelectMultiple)
    positions = forms.MultipleChoiceField(label=_("Historische Positionen"), widget=forms.CheckboxSelectMultiple)

    def __init__(self, *args, snapshot, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["participants"].choices = [(p["id"], p["name"]) for p in snapshot.payload["participants"]]
        self.fields["positions"].choices = [
            (p["id"], f"{p['order']}. {p['title']}") for p in snapshot.payload["positions"]
        ]


@never_cache
@login_required
@require_GET
def project_runs(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    runs = (
        GenerationRun.objects.filter(snapshot__project=project)
        .select_related("snapshot", "job")
        .order_by("-created_at")[:100]
    )
    return render(request, "exports/runs.html", {"project": project, "runs": runs})


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def contents(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    context, status = {"project": project, "contents_only": True}, 200
    try:
        report = contents_report(project.pk)
        context.update(report=report, token=selection_token(report, request.user))
        if request.method == "POST":
            run = authorize_selection(report, request.POST.get("token", ""), [], request.user)
            return redirect("generation_detail", run.pk)
    except (ValidationError, OSError) as exc:
        context["error"] = (
            " ".join(exc.messages) if isinstance(exc, ValidationError) else _("Eingaben nicht verfügbar.")
        )
        status = 409
    return render(request, "exports/selection.html", context, status=status)


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def historical(request, snapshot_id):
    snapshot = get_object_or_404(GenerationSnapshot, pk=snapshot_id, kind__in=["FULL", "EXCERPT"])
    selection = HistoricalSelection(request.POST if request.method == "POST" else None, snapshot=snapshot)
    context, status = {"source": snapshot, "selection": selection}, 200
    if request.method == "POST" and selection.is_valid():
        try:
            report = historical_report(
                snapshot.pk, selection.cleaned_data["participants"], selection.cleaned_data["positions"]
            )
            context.update(report=report, token=selection_token(report, request.user))
            if request.POST.get("action") == "authorize":
                run = authorize_selection(
                    report, request.POST.get("token", ""), request.POST.getlist("acknowledgements"), request.user
                )
                return redirect("generation_detail", run.pk)
        except (ValidationError, OSError) as exc:
            context["error"] = (
                " ".join(exc.messages)
                if isinstance(exc, ValidationError)
                else _("Historische Eingaben nicht verfügbar.")
            )
            status = 409
    elif request.method == "POST":
        status = 400
    return render(request, "exports/selection.html", context, status=status)
