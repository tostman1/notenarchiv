"""Thin ensemble CRUD and mapping overview; no independent musical resolver."""

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.projects import ensemble_services as service
from apps.projects import models as m
from apps.projects.ensemble_forms import MappingForm, ParticipantRoleForm, RoleForm
from apps.projects.forms import RevisionForm
from apps.projects.services import ProjectConflict

STATUS = {
    "MAPPED": _("Explizit zugeordnet"),
    "MISSING": _("Mapping fehlt — keine automatische Stammstimme"),
    "INVALID_ROLE": _("Rolle fehlt oder ist inaktiv"),
    "INVALID_MAPPING": _("Mapping ungültig; ausdrücklich korrigieren"),
}


@never_cache
@login_required
@require_GET
def overview(request, project_id):
    project = get_object_or_404(m.Project, pk=project_id)
    people = Paginator(
        project.participants.filter(active=True)
        .select_related("role", "default_part__instrument")
        .order_by("display_name", "pk"),
        25,
    ).get_page(request.GET.get("people"))
    position = None
    if request.GET.get("position"):
        try:
            position = get_object_or_404(
                project.positions.filter(active=True, arrangement__isnull=False), pk=request.GET["position"]
            )
        except (ValidationError, ValueError):
            raise Http404 from None
    mappings = list(
        m.EnsembleMapping.objects.filter(project=project).select_related(
            "role", "part__instrument", "position__arrangement__work"
        )[:20_001]
    )
    if len(mappings) > service.MAX_MAPPINGS:
        return HttpResponse(_("Zu viele Ensemble-Mappings; Projektbestand kontrollieren."), status=400)
    rows = []
    for person in people:
        result = (
            service.mapping_choice(
                project.pk,
                person.role_id,
                person.default_part.instrument_id,
                position.pk if position else None,
                mappings=mappings,
                role=person.role,
            )
            if person.role_id
            else None
        )
        rows.append(
            {
                "person": person,
                "choice": result,
                "status": STATUS[result.status] if result else _("Keine Rolle — gespeicherte Projektstimme"),
                "form": ParticipantRoleForm(
                    project=project,
                    prefix=str(person.pk),
                    initial={"role": person.role_id, "expected_revision": project.revision},
                ),
            }
        )
    return render(
        request,
        "projects/ensemble.html",
        {
            "project": project,
            "rows": rows,
            "people": people,
            "position": position,
            "positions": project.positions.filter(active=True, arrangement__isnull=False).select_related(
                "arrangement__work"
            )[:1000],
            "roles": Paginator(project.roles.order_by("code_key", "pk"), 25).get_page(request.GET.get("roles")),
            "mappings": Paginator(mappings, 25).get_page(request.GET.get("mappings")),
            "revision_form": RevisionForm(initial={"expected_revision": project.revision}),
        },
    )


def form_response(request, project, form, title, status=200):
    return render(
        request, "projects/ensemble_form.html", {"project": project, "form": form, "title": title}, status=status
    )


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def role_edit(request, project_id, role_id=None):
    project = get_object_or_404(m.Project, pk=project_id)
    role = get_object_or_404(project.roles, pk=role_id) if role_id else None
    form = RoleForm(
        request.POST if request.method == "POST" else None,
        initial={
            "expected_revision": project.revision,
            "code": role.code if role else "",
            "label": role.label if role else "",
        },
    )
    status = 200
    if request.method == "POST":
        status = 400
        if form.is_valid():
            try:
                service.save_role(project.pk, role_id=role_id, actor=request.user, **form.cleaned_data)
            except ProjectConflict as error:
                form.add_error(None, error)
                status = 409
            except ValidationError:
                form.add_error(None, _("Rolle ungültig oder Kürzel bereits vorhanden; nichts gespeichert."))
            else:
                return redirect("project_ensemble", project_id=project.pk)
    return form_response(request, project, form, _("Musikalische Rolle bearbeiten"), status)


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def mapping_edit(request, project_id, mapping_id=None):
    project = get_object_or_404(m.Project, pk=project_id)
    mapping = get_object_or_404(m.EnsembleMapping, project=project, pk=mapping_id) if mapping_id else None
    initial = {"expected_revision": project.revision}
    if mapping:
        initial.update(
            role=mapping.role_id, instrument=mapping.instrument_id, part=mapping.part_id, position=mapping.position_id
        )
    form = MappingForm(request.POST if request.method == "POST" else None, project=project, initial=initial)
    status = 200
    if request.method == "POST":
        status = 400
        if form.is_valid():
            data = form.cleaned_data
            try:
                service.save_mapping(
                    project.pk,
                    mapping_id=mapping_id,
                    role_id=data["role"].pk,
                    instrument_id=data["instrument"].pk,
                    part_id=data["part"].pk,
                    position_id=data["position"].pk if data["position"] else None,
                    actor=request.user,
                    expected_revision=data["expected_revision"],
                )
            except ProjectConflict as error:
                form.add_error(None, error)
                status = 409
            except ValidationError:
                form.add_error(None, _("Mapping nicht gültig oder Geltungsbereich bereits belegt; nichts gespeichert."))
            else:
                return redirect("project_ensemble", project_id=project.pk)
    return form_response(request, project, form, _("Rolle auf spielbare Stimme zuordnen"), status)


@never_cache
@login_required
@require_POST
def participant_role(request, project_id, participant_id):
    project = get_object_or_404(m.Project, pk=project_id)
    get_object_or_404(project.participants, pk=participant_id)
    form = ParticipantRoleForm(request.POST, project=project, prefix=str(participant_id))
    status = 400
    if form.is_valid():
        try:
            service.assign_role(
                project.pk,
                participant_id,
                form.cleaned_data["role"].pk if form.cleaned_data["role"] else None,
                actor=request.user,
                expected_revision=form.cleaned_data["expected_revision"],
            )
        except ProjectConflict as error:
            form.add_error(None, error)
            status = 409
        except ValidationError:
            form.add_error(None, _("Rolle konnte nicht sicher zugewiesen werden."))
        else:
            return redirect("project_ensemble", project_id=project.pk)
    return form_response(request, project, form, _("Teilnehmerrolle nicht gespeichert"), status)


@never_cache
@login_required
@require_POST
def state(request, project_id, kind, record_id):
    project = get_object_or_404(m.Project, pk=project_id)
    target = get_object_or_404(
        project.roles if kind == "role" else m.EnsembleMapping.objects.filter(project=project), pk=record_id
    )
    form = RevisionForm(request.POST)
    status = 400
    if form.is_valid():
        try:
            kwargs = {"actor": request.user, "expected_revision": form.cleaned_data["expected_revision"]}
            if kind == "role":
                service.set_role_active(project.pk, target.pk, active=not target.active, **kwargs)
            else:
                service.clear_mapping(project.pk, target.pk, **kwargs)
        except ProjectConflict as error:
            form.add_error(None, error)
            status = 409
        except ValidationError:
            form.add_error(None, _("Zuordnung zuerst ausdrücklich lösen; referenzierte Rollen bleiben geschützt."))
        else:
            return redirect("project_ensemble", project_id=project.pk)
    return form_response(request, project, form, _("Ensembleänderung nicht gespeichert"), status)
