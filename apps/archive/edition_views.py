"""Thin authenticated preference UI; compatibility rules live in services."""

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from apps.archive import edition_services as service
from apps.archive import library_services
from apps.archive import models as m
from apps.archive.services import ArchiveConflict
from apps.catalog.models import Arrangement, Part


class PreferenceForm(forms.Form):
    expected_revision = forms.IntegerField(min_value=1, widget=forms.HiddenInput)
    assignment = forms.UUIDField(required=False, widget=forms.HiddenInput)


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def editions(request, arrangement_id, part_id):
    arrangement = get_object_or_404(
        Arrangement.objects.select_related("work"), pk=arrangement_id, active=True, work__active=True
    )
    part = get_object_or_404(Part.objects.select_related("instrument"), pk=part_id)
    form = PreferenceForm(request.POST if request.method == "POST" else None)
    status = 200
    if request.method == "POST":
        if form.is_valid():
            try:
                service.set_preference(
                    arrangement.pk,
                    part.pk,
                    form.cleaned_data["assignment"],
                    actor=request.user,
                    expected_revision=form.cleaned_data["expected_revision"],
                )
            except ArchiveConflict:
                form.add_error(None, _("Archiv oder Bevorzugung geändert. Bitte neu laden und erneut wählen."))
                status = 409
            except ValidationError:
                form.add_error(None, _("Ausgabe nicht passend, unbestätigt, zurückgezogen oder beschädigt."))
                status = 400
            else:
                messages.success(
                    request, _("Archivweite Bevorzugung gespeichert. Explizite Ausgaben bleiben unverändert.")
                )
                return redirect("archive_editions", arrangement_id=arrangement.pk, part_id=part.pk)
        else:
            status = 400
    preference = (
        m.PreferredEdition.objects.filter(arrangement=arrangement, part=part).select_related("assignment").first()
    )
    page = Paginator(
        m.ArchiveAssignment.objects.filter(part=part, archive_file__arrangement=arrangement)
        .select_related("archive_file__source_version", "part__instrument")
        .order_by("-created_at", "pk"),
        20,
    ).get_page(request.GET.get("page"))
    eligible = set(
        service.compatible(arrangement.pk, part.pk)
        .filter(pk__in=[item.pk for item in page])
        .values_list("pk", flat=True)
    )
    for assignment in page:
        assignment.available = assignment.pk in eligible and library_services.verify_file(assignment.archive_file)
        assignment.preferred = bool(preference and preference.assignment_id == assignment.pk)
        assignment.kind_label = (
            _("Originalgetreue Kopie")
            if assignment.archive_file.kind == "BASE"
            else _("Separat freigegebene Bearbeitung")
        )
    explicit = request.GET.get("selection")
    resolution = service.resolve(arrangement.pk, part.pk, explicit_assignment_id=explicit)
    return render(
        request,
        "archive/editions.html",
        {
            "arrangement": arrangement,
            "part": part,
            "page": page,
            "preference": preference,
            "resolution": resolution,
            "form": form,
            "selection": explicit,
            "changes": preference.changes.select_related("previous__archive_file", "selected__archive_file")[:10]
            if preference
            else [],
        },
        status=status,
    )
