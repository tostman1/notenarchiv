"""Thin participant selection/default screens; no hidden master-data refresh."""

from django.contrib.auth.decorators import login_required
from django.core import signing
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.catalog.models import normalized
from apps.members.models import Member
from apps.projects import participant_services as service
from apps.projects.forms import RevisionForm
from apps.projects.models import Project, ProjectParticipant
from apps.projects.participant_forms import DefaultForm, GuestForm, ParticipantFilters
from apps.projects.services import ProjectConflict

SALT = "project.member-selection.v1"


@never_cache
@login_required
@require_GET
def participants(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    form = ParticipantFilters(request.GET)
    members = Member.objects.filter(active=True).select_related("regular_part__instrument")
    valid = form.is_valid()
    if valid:
        if form.cleaned_data["q"]:
            members = members.filter(name_key__contains=normalized(form.cleaned_data["q"]))
        if form.cleaned_data["instrument"]:
            members = members.filter(regular_part__instrument=form.cleaned_data["instrument"])
    else:
        members = members.none()
    page = Paginator(members.order_by("name_key", "pk"), 25).get_page(request.GET.get("page"))
    selected_ids = set(
        project.participants.filter(active=True, member__isnull=False).values_list("member_id", flat=True)
    )
    for member in page:
        member.selected = member.pk in selected_ids
    token = signing.dumps(
        {
            "actor": str(request.user.pk),
            "project": str(project.pk),
            "revision": project.revision,
            "scope": [str(member.pk) for member in page],
        },
        salt=SALT,
        compress=True,
    )
    parameters = request.GET.copy()
    parameters.pop("page", None)
    parameters.pop("participants", None)
    selected = Paginator(
        project.participants.select_related(
            "default_part__instrument", "member__regular_part__instrument", "role"
        ).order_by("display_name", "pk"),
        25,
    ).get_page(request.GET.get("participants"))
    return render(
        request,
        "projects/participants.html",
        {
            "project": project,
            "form": form,
            "members": page,
            "scope_token": token,
            "selected": selected,
            "filters": parameters.urlencode(),
            "guest_form": GuestForm(initial={"expected_revision": project.revision}),
        },
        status=200 if valid else 400,
    )


def action_error(request, project, form, status):
    return render(request, "projects/action_error.html", {"project": project, "form": form}, status=status)


@never_cache
@login_required
@require_POST
def select(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    form = RevisionForm(request.POST)
    status = 400
    if form.is_valid():
        try:
            action = request.POST.get("action")
            args = {"actor": request.user, "expected_revision": form.cleaned_data["expected_revision"]}
            if action == "all":
                service.select_all_members(project.pk, **args)
            elif action == "none":
                service.deselect_all(project.pk, **args)
            elif action == "subset":
                token = request.POST.get("scope", "")
                if len(token) > 32768:
                    raise ValidationError(_("Auswahl zu groß."))
                payload = signing.loads(token, salt=SALT, max_age=900)
                if (payload["actor"], payload["project"], payload["revision"]) != (
                    str(request.user.pk),
                    str(project.pk),
                    args["expected_revision"],
                ):
                    raise ProjectConflict()
                service.member_subset(project.pk, request.POST.getlist("member"), scope_ids=payload["scope"], **args)
            else:
                raise ValidationError(_("Ungültige Teilnehmerauswahl."))
        except (ProjectConflict, signing.BadSignature):
            form.add_error(None, _("Auswahl geändert oder abgelaufen; bitte neu laden."))
            status = 409
        except (ValidationError, KeyError, TypeError, ValueError):
            form.add_error(None, _("Ungültige Teilnehmerauswahl; keine Teiländerung gespeichert."))
        else:
            return redirect("project_participants", project_id=project.pk)
    return action_error(request, project, form, status)


@never_cache
@login_required
@require_POST
def guest(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    form = GuestForm(request.POST)
    status = 400
    if form.is_valid():
        try:
            service.add_guest(
                project.pk,
                name=form.cleaned_data["name"],
                part_id=form.cleaned_data["part"].pk,
                actor=request.user,
                expected_revision=form.cleaned_data["expected_revision"],
            )
        except ProjectConflict as error:
            form.add_error(None, error)
            status = 409
        except ValidationError:
            form.add_error(None, _("Gast benötigt eine gültige spielbare Stimme."))
        else:
            return redirect("project_participants", project_id=project.pk)
    return action_error(request, project, form, status)


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def default(request, project_id, participant_id):
    project = get_object_or_404(Project, pk=project_id)
    participant = get_object_or_404(ProjectParticipant, pk=participant_id, project=project)
    form = DefaultForm(
        request.POST if request.method == "POST" else None,
        initial={"expected_revision": project.revision, "part": participant.default_part_id},
    )
    status = 200
    if request.method == "POST":
        status = 400
        if form.is_valid():
            try:
                service.change_participant(
                    project.pk,
                    participant.pk,
                    action="default",
                    part_id=form.cleaned_data["part"].pk,
                    actor=request.user,
                    expected_revision=form.cleaned_data["expected_revision"],
                )
            except ProjectConflict as error:
                form.add_error(None, error)
                status = 409
            except ValidationError:
                form.add_error(None, _("Ungültige Projektstimme."))
            else:
                return redirect("project_participants", project_id=project.pk)
    return render(
        request,
        "projects/participant_default.html",
        {"project": project, "participant": participant, "form": form},
        status=status,
    )


@never_cache
@login_required
@require_POST
def change(request, project_id, participant_id):
    project = get_object_or_404(Project, pk=project_id)
    get_object_or_404(ProjectParticipant, pk=participant_id, project=project)
    form = RevisionForm(request.POST)
    status = 400
    if form.is_valid():
        try:
            member_revision = request.POST.get("member_revision")
            service.change_participant(
                project.pk,
                participant_id,
                actor=request.user,
                expected_revision=form.cleaned_data["expected_revision"],
                action=request.POST.get("action"),
                expected_member_revision=int(member_revision) if member_revision else None,
                refresh_name=request.POST.get("refresh_name") == "on",
            )
        except ProjectConflict as error:
            form.add_error(None, error)
            status = 409
        except (ValidationError, ValueError):
            form.add_error(None, _("Teilnehmeraktion nicht möglich; gespeicherte Zuordnungen bleiben erhalten."))
        else:
            return redirect("project_participants", project_id=project.pk)
    return action_error(request, project, form, status)
