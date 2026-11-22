"""Thin authenticated replacement/edition rule UI; no second assignment resolver."""

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.archive import library_services
from apps.archive.models import ArchiveAssignment
from apps.projects import models as m
from apps.projects import rule_services as service
from apps.projects.forms import RevisionForm
from apps.projects.rule_forms import EditionForm, ReplacementForm
from apps.projects.services import ProjectConflict


def destination(project):
    return redirect("project_rules", project_id=project.pk) if project else redirect("global_replacement_rules")


def edition_page(query, number):
    page = Paginator(query.order_by("pk"), 25).get_page(number)
    eligible = set(
        ArchiveAssignment.objects.usable()
        .filter(pk__in=[item.edition_id for item in page])
        .values_list("pk", flat=True)
    )
    for item in page:
        item.material_status = (
            _("Bestätigt und hash-geprüft")
            if item.edition_id in eligible and library_services.verify_file(item.edition.archive_file)
            else _("Gewählte Ausgabe zurückgezogen, fehlend oder beschädigt; keine Ersatzwahl")
        )
    return page


@never_cache
@login_required
@require_GET
def overview(request, project_id=None):
    project = get_object_or_404(m.Project, pk=project_id) if project_id else None
    revision = project.revision if project else m.GlobalRuleState.objects.get(pk=1).revision
    replacements = (
        m.ReplacementRule.objects.filter(project=project) if project else m.GlobalReplacementRule.objects.all()
    )
    replacements = replacements.select_related("desired_part__instrument", "replacement_part__instrument").order_by(
        "pk"
    )
    return render(
        request,
        "projects/rules.html",
        {
            "project": project,
            "revision": revision,
            "replacements": Paginator(replacements, 25).get_page(request.GET.get("rules")),
            "project_editions": edition_page(
                m.ProjectEditionPreference.objects.filter(project=project)
                .select_related("arrangement__work", "part__instrument", "edition__archive_file")
                .order_by("pk"),
                request.GET.get("editions"),
            )
            if project
            else [],
            "position_editions": edition_page(
                m.PositionEditionPreference.objects.filter(project=project)
                .select_related("position__arrangement__work", "part__instrument", "edition__archive_file")
                .order_by("pk"),
                request.GET.get("positions"),
            )
            if project
            else [],
            "form": RevisionForm(initial={"expected_revision": revision}),
        },
    )


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def replacement_edit(request, project_id=None, rule_id=None):
    project = get_object_or_404(m.Project, pk=project_id) if project_id else None
    query = m.ReplacementRule.objects.filter(project=project) if project else m.GlobalReplacementRule.objects.all()
    rule = get_object_or_404(query, pk=rule_id) if rule_id else None
    initial = {"expected_revision": project.revision if project else m.GlobalRuleState.objects.get(pk=1).revision}
    if rule:
        initial.update(desired_part=rule.desired_part_id, replacement_part=rule.replacement_part_id)
        if project:
            initial["position"] = rule.position_id
    form = ReplacementForm(request.POST if request.method == "POST" else None, project=project, initial=initial)
    status = 200
    if request.method == "POST":
        status = 400
        if form.is_valid():
            data = form.cleaned_data
            try:
                service.save_replacement(
                    project_id=project_id,
                    rule_id=rule_id,
                    position_id=data["position"].pk if data.get("position") else None,
                    desired_part_id=data["desired_part"].pk,
                    replacement_part_id=data["replacement_part"].pk,
                    actor=request.user,
                    expected_revision=data["expected_revision"],
                )
            except ProjectConflict as error:
                form.add_error(None, error)
                status = 409
            except ValidationError as error:
                form.add_error(None, error)
            else:
                return destination(project)
    return render(
        request,
        "projects/rule_form.html",
        {"project": project, "form": form, "title": _("Explizite Ersatzregel")},
        status=status,
    )


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def edition_edit(request, project_id):
    project = get_object_or_404(m.Project, pk=project_id)
    form = EditionForm(
        request.POST if request.method == "POST" else None,
        project=project,
        initial={"expected_revision": project.revision},
    )
    status = 200
    if request.method == "POST":
        status = 400
        if form.is_valid():
            data = form.cleaned_data
            try:
                service.set_edition(
                    project.pk,
                    arrangement_id=data["arrangement"].pk,
                    part_id=data["part"].pk,
                    edition_id=data["edition"].pk,
                    position_id=data["position"].pk if data["position"] else None,
                    actor=request.user,
                    expected_revision=data["expected_revision"],
                )
            except ProjectConflict as error:
                form.add_error(None, error)
                status = 409
            except ValidationError:
                form.add_error(None, _("Ausgabe nicht bestätigt, unpassend oder beschädigt; nichts gespeichert."))
            else:
                return destination(project)
    return render(
        request,
        "projects/rule_form.html",
        {"project": project, "form": form, "title": _("Konkrete Ausgabenpräferenz")},
        status=status,
    )


@never_cache
@login_required
@require_POST
def clear(request, kind, record_id, project_id=None):
    project = get_object_or_404(m.Project, pk=project_id) if project_id else None
    model = {
        "replacement": m.ReplacementRule if project else m.GlobalReplacementRule,
        "project-edition": m.ProjectEditionPreference,
        "position-edition": m.PositionEditionPreference,
    }[kind]
    query = model.objects.filter(project=project) if project else model.objects.all()
    get_object_or_404(query, pk=record_id)
    form = RevisionForm(request.POST)
    status = 400
    if form.is_valid():
        try:
            args = {"actor": request.user, "expected_revision": form.cleaned_data["expected_revision"]}
            if kind == "replacement":
                service.clear_replacement(record_id, project_id=project_id, **args)
            else:
                service.clear_edition(project.pk, record_id, position_scope=kind == "position-edition", **args)
        except ProjectConflict as error:
            form.add_error(None, error)
            status = 409
        except ValidationError as error:
            form.add_error(None, error)
        else:
            return destination(project)
    return render(
        request,
        "projects/rule_form.html",
        {"project": project, "form": form, "title": _("Regel nicht zurückgesetzt")},
        status=status,
    )
