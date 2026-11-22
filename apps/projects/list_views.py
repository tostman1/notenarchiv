"""Thin German shared-list UI and local live library selection."""

from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST

from apps.archive.library_forms import LibraryFilters
from apps.archive.library_services import search
from apps.projects import list_services as service
from apps.projects.models import Project
from apps.projects.services import ProjectConflict


class ListAction(forms.Form):
    expected_revision = forms.IntegerField(min_value=1, widget=forms.HiddenInput)
    action = forms.ChoiceField(
        choices=[(value, value) for value in ["insert", "reserve", "move", "replace", "remove", "reorder"]]
    )
    position = forms.UUIDField(required=False)
    arrangement = forms.UUIDField(required=False)
    at = forms.IntegerField(min_value=1, max_value=1001, required=False)
    acknowledge = forms.BooleanField(required=False)

    def clean(self):
        values = super().clean()
        if "participant" in self.data or "member" in self.data:
            raise forms.ValidationError(_("Die Stückliste ist gemeinsam; keine personenbezogenen Änderungen."))
        return values


@never_cache
@login_required
@require_GET
def piece_list(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    rows = list(
        service.positions(project).annotate(
            invalid_overrides=Count("overrides", filter=Q(overrides__needs_revalidation=True), distinct=True),
            invalid_editions=Count(
                "edition_preferences", filter=Q(edition_preferences__needs_revalidation=True), distinct=True
            ),
        )[:1000]
    )
    return render(
        request,
        "projects/pieces.html",
        {
            "project": project,
            "positions": rows,
            "review_count": sum(row.invalid_overrides + row.invalid_editions for row in rows),
        },
    )


@never_cache
@login_required
@require_GET
def library_selection(request, project_id):
    project = get_object_or_404(Project, pk=project_id, status="ACTIVE")
    form = LibraryFilters(request.GET)
    valid = form.is_valid()
    page = Paginator(search(form.cleaned_data) if valid else search({}).none(), 25).get_page(request.GET.get("page"))
    parameters = request.GET.copy()
    parameters.pop("page", None)
    return render(
        request,
        "projects/library_selection.html",
        {
            "project": project,
            "form": form,
            "page": page,
            "filters": parameters.urlencode(),
            "at": request.GET.get("at", ""),
            "position": request.GET.get("position", ""),
        },
        status=200 if valid else 400,
    )


@never_cache
@login_required
@require_POST
def mutate(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    form = ListAction(request.POST)
    status = 400
    if form.is_valid():
        data = form.cleaned_data
        kwargs = {"actor": request.user, "expected_revision": data["expected_revision"]}
        try:
            action = data["action"]
            if action in {"insert", "reserve"}:
                if action == "insert" and not data["arrangement"]:
                    raise ValidationError(_("Wählen Sie ein konkretes Arrangement."))
                service.insert(
                    project.pk,
                    arrangement_id=data["arrangement"] if action == "insert" else None,
                    at=data["at"],
                    **kwargs,
                )
            elif action == "move":
                service.move(project.pk, data["position"], data["at"], **kwargs)
            elif action == "replace":
                service.replace(
                    project.pk, data["position"], data["arrangement"], acknowledge=data["acknowledge"], **kwargs
                )
            elif action == "remove":
                service.remove(project.pk, data["position"], **kwargs)
            else:
                service.reorder(project.pk, request.POST.getlist("order"), **kwargs)
        except ProjectConflict as error:
            form.add_error(None, error)
            status = 409
        except ValidationError as error:
            form.add_error(None, error)
        else:
            return redirect("project_piece_list", project_id=project.pk)
    return render(request, "projects/action_error.html", {"project": project, "form": form}, status=status)
