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


class BatchEditForm(RevisionForm):
    part = forms.ModelChoiceField(label=_("Mehrfachziel: Stimme und Notation"), queryset=None, required=False)
    action = forms.ChoiceField(choices=[("save", "save"), ("reset", "reset")], widget=forms.HiddenInput)
    rows = forms.IntegerField(min_value=1, required=False, widget=forms.HiddenInput)
    people = forms.IntegerField(min_value=1, required=False, widget=forms.HiddenInput)

    def __init__(self, *args, **kwargs):
        from apps.catalog.models import Part

        super().__init__(*args, **kwargs)
        self.fields["part"].queryset = Part.objects.filter(active=True, instrument__active=True).select_related(
            "instrument"
        )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("action") == "save" and cleaned.get("part") is None:
            self.add_error("part", _("Für Mehrfachänderungen eine gemeinsame Stimme und Notation wählen."))
        return cleaned
