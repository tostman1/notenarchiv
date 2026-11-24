"""German durable project settings; no domain identities accepted as free text."""

from django import forms
from django.utils.translation import gettext_lazy as _

from apps.projects.models import Project


class ProjectForm(forms.ModelForm):
    expected_revision = forms.IntegerField(min_value=0, widget=forms.HiddenInput)

    class Meta:
        model = Project
        fields = ["name", "layout", "width_mm", "height_mm", "cover_enabled", "cover_title"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial["expected_revision"] = self.instance.revision if not self.instance._state.adding else 0
        self.fields["layout"].help_text = _(
            "Normale Mappen: Lese- und reguläre A4/A3-Druck-PDF verfügbar. "
            "Marschbuch: Konfiguration vorhanden; spezifisches Drucklayout noch nicht verfügbar (WP-42)."
        )


class RevisionForm(forms.Form):
    expected_revision = forms.IntegerField(min_value=1, widget=forms.HiddenInput)


class DuplicateForm(RevisionForm):
    name = forms.CharField(label=_("Name der Kopie"), max_length=200)
