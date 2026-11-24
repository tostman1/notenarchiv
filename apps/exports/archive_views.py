"""Explicit secure archive print selection, preserving unchanged direct downloads."""

from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from apps.archive.models import ArchiveFile
from apps.exports import archive_services


class ArchiveSelection(forms.Form):
    files = forms.MultipleChoiceField(
        label=_("Bestätigte Archivdateien für Druck-PDF"), widget=forms.CheckboxSelectMultiple
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        selected = (
            ArchiveFile.objects.usable()
            .select_related("arrangement__work")
            .order_by("arrangement__work__title", "pk")[:501]
        )
        self.fields["files"].choices = [(str(f.pk), f"{f.arrangement} · {f.pk}") for f in selected]


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def generate(request):
    form = ArchiveSelection(request.POST if request.method == "POST" else None)
    context, status = {"form": form}, 200
    if request.method == "POST" and form.is_valid():
        try:
            selected = archive_services.report(form.cleaned_data["files"])
            context.update(selected=selected, token=archive_services.token(selected, request.user))
            if request.POST.get("action") == "authorize":
                run = archive_services.authorize(
                    form.cleaned_data["files"], request.POST.get("token", ""), request.user
                )
                return redirect("generation_detail", run.pk)
        except (ValidationError, ValueError, OSError):
            context["error"] = _(
                "Archivdateien geändert, beschädigt oder nicht freigegeben; erneut auswählen und prüfen."
            )
            status = 409
    elif request.method == "POST":
        status = 400
    return render(request, "exports/archive_selection.html", context, status=status)
