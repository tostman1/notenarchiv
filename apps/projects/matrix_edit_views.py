"""Authenticated revision-guarded matrix mutations and HTMX/no-JS responses."""

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from apps.projects import matrix_edit_services, participant_services
from apps.projects.matrix_edit_context import add_edit_forms
from apps.projects.matrix_forms import CellEditForm
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
    if request.headers.get("HX-Request") == "true":
        try:
            context = add_edit_forms(matrix_page(project.pk, row_page=row_page, column_page=column_page), request.user)
        except ValidationError:
            return HttpResponse(_("Matrix kann nicht geladen werden; Projekt neu öffnen."), status=409)
        context["edit_message"] = message
        context["edit_error"] = status != 200
        return render(request, "projects/matrix_panel.html", context, status=status)
    if status != 200:
        return render(
            request, "projects/matrix_edit_error.html", {"project": project, "message": message}, status=status
        )
    url = reverse("project_matrix", args=[project.pk])
    return redirect(url + f"?rows={row_page or 1}&people={column_page or 1}")


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
