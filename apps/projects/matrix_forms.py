"""Exact confirmed edition choices include playable part, notation and version."""

from django import forms
from django.utils.translation import gettext_lazy as _

from apps.projects.forms import RevisionForm


class CellEditForm(RevisionForm):
    choice = forms.CharField(label=_("Spielbare Stimme und konkrete Ausgabe"), max_length=4096, widget=forms.Select)
    rows = forms.IntegerField(min_value=1, required=False, widget=forms.HiddenInput)
    people = forms.IntegerField(min_value=1, required=False, widget=forms.HiddenInput)

    def __init__(self, *args, choices=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["choice"].widget.choices = [("", _("Bestätigte Stimme / Notation / Version wählen")), *choices]
        self.fields["choice"].widget.attrs["required"] = True
