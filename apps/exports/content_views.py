"""Authenticated explicit selection of already inspected musical content."""

from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from apps.archive.content_services import ArchiveConflict
from apps.archive.models import ContentEdition
from apps.exports import content_export_services


class ContentSelection(forms.Form):
    editions = forms.MultipleChoiceField(label=_("Inhaltsausgaben"), widget=forms.CheckboxSelectMultiple)
    variant = forms.ChoiceField(
        label=_("PDF-Ausgabeart"), choices=[("READING", _("Lese-PDF")), ("PRINT", _("Druck-PDF"))]
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        editions = (
            ContentEdition.objects.filter(arrangement__active=True, arrangement__work__active=True, part__active=True)
            .select_related("arrangement__work", "part__instrument")
            .order_by("arrangement__work__title", "pk")[:501]
        )
        self.fields["editions"].choices = [(str(e.pk), f"{e.arrangement} · {e.part} · {e.pk}") for e in editions]


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def generate(request):
    form = ContentSelection(request.POST if request.method == "POST" else None)
    context, status = {"form": form}, 200
    if request.method == "POST" and form.is_valid():
        try:
            selected = content_export_services.report(form.cleaned_data["editions"])
            variant = form.cleaned_data["variant"]
            context.update(
                selected=selected,
                variant=variant,
                token=content_export_services.token(selected, request.user, variant),
            )
            if request.POST.get("action") == "authorize":
                run = content_export_services.authorize(
                    form.cleaned_data["editions"], request.POST.get("token", ""), request.user, variant
                )
                return redirect("generation_detail", run.pk)
        except (ValidationError, ArchiveConflict, ObjectDoesNotExist, ValueError, OSError):
            context["error"] = _("Inhalte nicht bestätigt, geändert oder beschädigt; erneut auswählen und prüfen.")
            status = 409
    elif request.method == "POST":
        status = 400
    return render(request, "exports/content_selection.html", context, status=status)
