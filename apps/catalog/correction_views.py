"""Explicit authenticated corrections preserve catalog history."""

from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from apps.catalog.collection_services import correct_membership, withdraw_association
from apps.catalog.models import CollectionMembership, Work, WorkAlternativeTitle, WorkRelationship

TARGETS = {
    "membership": CollectionMembership,
    "relationship": WorkRelationship,
    "alternative_title": WorkAlternativeTitle,
}


class CorrectionForm(forms.Form):
    revision = forms.IntegerField(min_value=1, widget=forms.HiddenInput)
    action = forms.ChoiceField(choices=(("withdraw", _("Zurücknehmen")), ("replace", _("Zuordnung ersetzen"))))
    reason = forms.CharField(max_length=500, label=_("Begründung"))
    work = forms.UUIDField(required=False, label=_("UUID des korrigierten Werkes"))
    position = forms.IntegerField(min_value=0, required=False, label=_("Position (ab 0)"))
    original_song_number = forms.CharField(max_length=80, required=False, label=_("Originale Liednummer"))


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def edit(request, kind, identifier):
    from django.http import Http404

    if kind not in TARGETS:
        raise Http404
    association = get_object_or_404(TARGETS[kind], pk=identifier)
    form = CorrectionForm(
        request.POST if request.method == "POST" else None, initial={"revision": association.revision}
    )
    status = 200
    if request.method == "POST":
        status = 400
        if form.is_valid():
            values = form.cleaned_data
            try:
                if values["action"] == "replace":
                    if kind != "membership" or values["work"] is None or values["position"] is None:
                        raise ValidationError("Replacement requires a membership, work and position.")
                    replacement = correct_membership(
                        identifier,
                        actor=request.user,
                        reason=values["reason"],
                        expected_revision=values["revision"],
                        work_id=values["work"],
                        position=values["position"],
                        original_song_number=values["original_song_number"],
                        local_overrides=association.local_overrides,
                    )
                    return redirect("catalog_correction", kind=kind, identifier=replacement.pk)
                withdraw_association(
                    kind, identifier, actor=request.user, reason=values["reason"], expected_revision=values["revision"]
                )
                return redirect("catalog_correction", kind=kind, identifier=identifier)
            except (ValidationError, ObjectDoesNotExist):
                form.add_error(
                    None, _("Korrektur nicht gespeichert. Bezug, Position und Revision bitte erneut prüfen.")
                )
                status = 409
    withdrawn = hasattr(association, "withdrawal")
    return render(
        request,
        "catalog/correction.html",
        {
            "association": association,
            "kind": kind,
            "form": form,
            "withdrawn": withdrawn,
            "work": Work.objects.filter(pk=getattr(association, "work_id", None)).first(),
        },
        status=status,
    )
