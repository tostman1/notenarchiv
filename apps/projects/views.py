"""Thin authenticated project CRUD; revisions and duplication live in services."""

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.catalog.models import normalized
from apps.projects import services
from apps.projects.forms import DuplicateForm, ProjectForm, RevisionForm
from apps.projects.models import Project


class SearchForm(forms.Form):
    q = forms.CharField(label=_("Projekt suchen"), required=False, max_length=200)
    status = forms.ChoiceField(
        label=_("Status"),
        required=False,
        choices=[("", _("Alle")), ("ACTIVE", _("Aktiv")), ("ARCHIVED", _("Archiviert"))],
    )


@never_cache
@login_required
@require_GET
def project_list(request):
    form = SearchForm(request.GET)
    query = Project.objects.all()
    if form.is_valid():
        if form.cleaned_data["q"]:
            query = query.filter(name_key__contains=normalized(form.cleaned_data["q"]))
        if form.cleaned_data["status"]:
            query = query.filter(status=form.cleaned_data["status"])
    page = Paginator(query, 25).get_page(request.GET.get("page"))
    parameters = request.GET.copy()
    parameters.pop("page", None)
    return render(
        request,
        "projects/list.html",
        {"form": form, "page": page, "filters": parameters.urlencode()},
        status=200 if form.is_valid() else 400,
    )


@never_cache
@login_required
@require_GET
def project_detail(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    return render(
        request,
        "projects/detail.html",
        {
            "project": project,
            "revision_form": RevisionForm(initial={"expected_revision": project.revision}),
            "duplicate_form": DuplicateForm(
                initial={"expected_revision": project.revision, "name": project.name + str(_(" (Kopie)"))}
            ),
            "positions": project.positions.filter(active=True).count(),
            "participants": project.participants.filter(active=True).count(),
            "history": project.history.order_by("-revision")[:20],
        },
    )


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def project_edit(request, project_id=None):
    project = get_object_or_404(Project, pk=project_id) if project_id else None
    form = ProjectForm(request.POST if request.method == "POST" else None, instance=project)
    status = 200
    if request.method == "POST":
        if form.is_valid():
            try:
                saved = services.save_project(
                    {key: form.cleaned_data[key] for key in services.FIELDS},
                    actor=request.user,
                    project_id=project_id,
                    expected_revision=form.cleaned_data["expected_revision"],
                )
            except services.ProjectConflict as error:
                form.add_error(None, error)
                status = 409
            except ValidationError:
                form.add_error(None, _("Projekteinstellungen konnten nicht sicher gespeichert werden."))
                status = 400
            else:
                messages.success(request, _("Projekt gespeichert."))
                return redirect("project_detail", project_id=saved.pk)
        else:
            status = 400
    return render(request, "projects/form.html", {"form": form, "project": project}, status=status)


@never_cache
@login_required
@require_POST
def project_duplicate(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    form = DuplicateForm(request.POST)
    status = 400
    if form.is_valid():
        try:
            clone = services.duplicate_project(
                project.pk,
                actor=request.user,
                expected_revision=form.cleaned_data["expected_revision"],
                name=form.cleaned_data["name"],
            )
        except services.ProjectConflict as error:
            form.add_error(None, error)
            status = 409
        except ValidationError:
            form.add_error(None, _("Projekt konnte nicht sicher dupliziert werden."))
        else:
            messages.success(request, _("Unabhängige Projektkopie erstellt."))
            return redirect("project_detail", project_id=clone.pk)
    return render(request, "projects/action_error.html", {"form": form, "project": project}, status=status)


@never_cache
@login_required
@require_POST
def project_archive(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    form = RevisionForm(request.POST)
    status = 400
    if form.is_valid():
        try:
            services.archive_project(
                project.pk,
                actor=request.user,
                expected_revision=form.cleaned_data["expected_revision"],
                archived=project.status == "ACTIVE",
            )
        except services.ProjectConflict as error:
            form.add_error(None, error)
            status = 409
        else:
            return redirect("project_detail", project_id=project.pk)
    return render(request, "projects/action_error.html", {"form": form, "project": project}, status=status)
