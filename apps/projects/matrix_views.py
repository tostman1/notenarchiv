"""Authenticated read-only matrix; templates never choose parts or editions."""

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, render
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from apps.projects.matrix_edit_context import add_edit_forms
from apps.projects.matrix_services import matrix_page
from apps.projects.models import Project


@never_cache
@login_required
@require_GET
def matrix(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    try:
        context = matrix_page(project.pk, row_page=request.GET.get("rows"), column_page=request.GET.get("people"))
        context = add_edit_forms(context, request.user)
    except ValidationError:
        return render(
            request,
            "projects/matrix.html",
            {
                "project": project,
                "matrix_error": _("Matrixauswahl geändert oder zu groß. Projekt neu laden und Auswahl kontrollieren."),
            },
            status=409,
        )
    return render(request, "projects/matrix.html", context)
