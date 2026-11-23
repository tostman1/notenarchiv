"""Authenticated read-only matrix; templates never choose parts or editions."""

from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, render
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from apps.projects.matrix_edit_context import add_edit_forms
from apps.projects.matrix_filters import MatrixFilters, navigation_values
from apps.projects.matrix_services import matrix_page
from apps.projects.models import Project


@never_cache
@login_required
@require_GET
def matrix(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    filters = MatrixFilters(request.GET, project=project)
    if not filters.is_valid():
        return render(
            request,
            "projects/matrix.html",
            {"project": project, "matrix_error": _("Ungültige Matrixfilter; Auswahl kontrollieren.")},
            status=400,
        )
    try:
        context = matrix_page(
            project.pk,
            row_page=request.GET.get("rows"),
            column_page=request.GET.get("people"),
            filters=filters.cleaned_data,
        )
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
    context["filter_form"] = filters
    context["navigation"] = navigation_values(request.GET)
    context["navigation_query"] = "&" + urlencode(context["navigation"])
    template = "projects/matrix_panel.html" if request.headers.get("HX-Request") == "true" else "projects/matrix.html"
    return render(request, template, context)
