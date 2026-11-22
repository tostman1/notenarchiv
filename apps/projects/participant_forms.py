"""Controlled German participant filters, guests and saved default edits."""

from django import forms
from django.utils.translation import gettext_lazy as _

from apps.catalog.models import InstrumentVariant, Part
from apps.projects.forms import RevisionForm


class ParticipantFilters(forms.Form):
    q = forms.CharField(label=_("Mitglied suchen"), max_length=160, required=False)
    instrument = forms.ModelChoiceField(
        label=_("Instrumentenvariante"), queryset=InstrumentVariant.objects.none(), required=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["instrument"].queryset = InstrumentVariant.objects.filter(active=True).order_by(
            "name_key", "transposition_key", "clef"
        )


class GuestForm(RevisionForm):
    name = forms.CharField(label=_("Name des Gasts"), max_length=160)
    part = forms.ModelChoiceField(label=_("Spielbare Gaststimme"), queryset=Part.objects.none())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["part"].queryset = (
            Part.objects.filter(active=True, instrument__active=True)
            .select_related("instrument")
            .order_by("instrument__name_key", "code_key")
        )


class DefaultForm(RevisionForm):
    part = forms.ModelChoiceField(label=_("Gespeicherte Projektstimme"), queryset=Part.objects.none())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["part"].queryset = (
            Part.objects.filter(active=True, instrument__active=True)
            .select_related("instrument")
            .order_by("instrument__name_key", "code_key")
        )
