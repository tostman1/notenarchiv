"""Authenticated revision-guarded matrix mutations and HTMX/no-JS responses."""

from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from apps.projects import matrix_batch_services, matrix_edit_services, participant_services
from apps.projects.matrix_edit_context import add_edit_forms
from apps.projects.matrix_filters import MatrixFilters, navigation_values
from apps.projects.matrix_forms import BatchEditForm, CellEditForm
from apps.projects.matrix_services import matrix_page
from apps.projects.models import Project
from apps.projects.participant_forms import DefaultForm
from apps.projects.services import ProjectConflict


def respond(request, project, *, status=200, message="", row_page=None, column_page=None):
    def page_number(value):
        try:
            return max(1, min(int(value or 1), 1000))
        except (TypeError, ValueError):
            return 1

    row_page, column_page = page_number(row_page), page_number(column_page)
    navigation = navigation_values(request.POST)
    filters = MatrixFilters(navigation, project=project)
    if not filters.is_valid():
        return HttpResponse(_("Ungültige Matrixfilter; Projekt neu öffnen."), status=400)
    if request.headers.get("HX-Request") == "true":
        try:
            context = add_edit_forms(
                matrix_page(project.pk, row_page=row_page, column_page=column_page, filters=filters.cleaned_data),
                request.user,
            )
        except ValidationError:
            return HttpResponse(_("Matrix kann nicht geladen werden; Projekt neu öffnen."), status=409)
        context["edit_message"] = message
        context["edit_error"] = status != 200
        context["filter_form"], context["navigation"] = filters, navigation
        context["navigation_query"] = "&" + urlencode(navigation)
        return render(request, "projects/matrix_panel.html", context, status=status)
    if status != 200:
        return render(
            request, "projects/matrix_edit_error.html", {"project": project, "message": message}, status=status
        )
    url = reverse("project_matrix", args=[project.pk])
    return redirect(url + "?" + urlencode({"rows": row_page, "people": column_page, **navigation}))


@never_cache
@login_required
@require_POST
def cell_edit(request, project_id, position_id, participant_id):
    project = get_object_or_404(Project, pk=project_id)
    get_object_or_404(project.positions, pk=position_id, active=True)
    get_object_or_404(project.participants, pk=participant_id, active=True)
    prefix = f"cell-{position_id}-{participant_id}"
    form = CellEditForm(request.POST, prefix=prefix)
    status, message = 400, _("Nur bestätigte passende Ausgabe wählen; nichts geändert.")
    if form.is_valid():
        try:
            matrix_edit_services.set_cell(
                project.pk,
                position_id,
                participant_id,
                form.cleaned_data["choice"],
                actor=request.user,
                expected_revision=form.cleaned_data["expected_revision"],
            )
        except ProjectConflict:
            status, message = 409, _("Projekt oder Archiv geändert. Neu laden und bewusst erneut wählen.")
        except ValidationError:
            pass
        else:
            status, message = 200, _("Persönliche Stimme und exakte Ausgabe gespeichert.")
    return respond(
        request,
        project,
        status=status,
        message=message,
        row_page=form.cleaned_data.get("rows"),
        column_page=form.cleaned_data.get("people"),
    )


@never_cache
@login_required
@require_POST
def default_edit(request, project_id, participant_id):
    project = get_object_or_404(Project, pk=project_id)
    get_object_or_404(project.participants, pk=participant_id, active=True)
    form = DefaultForm(request.POST, prefix=f"default-{participant_id}")
    status, message = 400, _("Projektdefault nicht gespeichert. Gültige spielbare Stimme wählen.")
    if form.is_valid():
        try:
            participant_services.change_participant(
                project.pk,
                participant_id,
                action="default",
                part_id=form.cleaned_data["part"].pk,
                actor=request.user,
                expected_revision=form.cleaned_data["expected_revision"],
            )
        except ProjectConflict:
            status, message = 409, _("Projekt geändert. Neu laden und bewusst erneut speichern.")
        except ValidationError:
            pass
        else:
            status, message = 200, _("Projektdefault gespeichert; persönliche Overrides bleiben erhalten.")
    return respond(
        request,
        project,
        status=status,
        message=message,
        row_page=request.POST.get("rows"),
        column_page=request.POST.get("people"),
    )


@never_cache
@login_required
@require_POST
def batch_edit(request, project_id, participant_id):
    project = get_object_or_404(Project, pk=project_id)
    get_object_or_404(project.participants, pk=participant_id, active=True)
    prefix = f"batch-{participant_id}"
    form = BatchEditForm(request.POST, prefix=prefix)
    status, message = (
        400,
        _("Mehrfachänderung ungültig; nichts geändert. Stimme, Zellen und konkrete Ausgaben kontrollieren."),
    )
    if form.is_valid():
        ids = request.POST.getlist(prefix + "-positions")
        try:
            if form.cleaned_data["action"] == "reset":
                count = matrix_batch_services.reset_cells(
                    project.pk,
                    participant_id,
                    ids,
                    actor=request.user,
                    expected_revision=form.cleaned_data["expected_revision"],
                )
                message = _("%(count)s persönliche Overrides zurückgesetzt; übrige Zellen bleiben unverändert.") % {
                    "count": count
                }
            else:
                selections = [
                    (identifier, request.POST.get(prefix + "-choice-" + identifier, "")) for identifier in ids
                ]
                matrix_batch_services.set_cells(
                    project.pk,
                    participant_id,
                    selections,
                    part_id=form.cleaned_data["part"].pk,
                    actor=request.user,
                    expected_revision=form.cleaned_data["expected_revision"],
                )
                message = _("Alle ausgewählten Zellen atomisch gespeichert.")
        except ProjectConflict:
            status, message = (
                409,
                _("Projekt oder Archiv geändert; gesamte Auswahl unverändert. Neu laden und erneut prüfen."),
            )
        except ValidationError as exc:
            message = " ".join(exc.messages)
        else:
            status = 200
    return respond(
        request,
        project,
        status=status,
        message=message,
        row_page=form.cleaned_data.get("rows"),
        column_page=form.cleaned_data.get("people"),
    )
