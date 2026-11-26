"""Explicit revision-fenced archive-wide content preference editing."""

from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from apps.archive.content_preferences import set_content_preference
from apps.archive.models import ContentEdition, PreferredEdition
from apps.archive.services import ArchiveConflict


class PreferenceAction(forms.Form):
    revision = forms.IntegerField(min_value=0, widget=forms.HiddenInput)
    action = forms.ChoiceField(choices=[("set", "set"), ("clear", "clear")])


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def edit(request, edition_id):
    edition = get_object_or_404(ContentEdition.objects.select_related("arrangement__work", "part"), pk=edition_id)
    preference = PreferredEdition.objects.filter(arrangement=edition.arrangement, part=edition.part).first()
    context = {"edition": edition, "preference": preference, "revision": edition.arrangement.revision}
    status = 200
    if request.method == "POST":
        form = PreferenceAction(request.POST)
        if not form.is_valid():
            context["error"] = _("Ungültige Aktion oder Revision; erneut öffnen.")
            status = 400
        else:
            try:
                set_content_preference(
                    edition.arrangement_id,
                    edition.part_id,
                    edition.pk if form.cleaned_data["action"] == "set" else None,
                    actor=request.user,
                    expected_revision=form.cleaned_data["revision"],
                )
                return redirect("content_preference", edition.pk)
            except (ArchiveConflict, ValidationError, ObjectDoesNotExist, OSError):
                context["error"] = _("Ausgabe oder Präferenz geändert, nicht bestätigt oder beschädigt; erneut prüfen.")
                status = 409
    return render(request, "exports/content_preference.html", context, status=status)
