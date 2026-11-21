"""Typed RAW-relative selections; the worker owns filesystem validation."""

from django import forms
from django.utils.translation import gettext_lazy as _

from core.paths import relative_path


class IndexSelection(forms.Form):
    folder = forms.CharField(
        label=_("RAW-Unterordner"),
        max_length=1024,
        required=False,
        help_text=_("Relativer Ordner, z. B. Marsch/Posaune. Leer bedeutet das gesamte Archiv. Keine absoluten Pfade."),
    )
    confirm = forms.BooleanField(label=_("Auswahl indizieren; neue und geänderte PDFs anschließend visuell prüfen"))

    def clean_folder(self):
        try:
            return relative_path(self.cleaned_data["folder"], allow_root=True)
        except ValueError:
            raise forms.ValidationError(
                _("Bitte einen gültigen RAW-relativen Ordner ohne Pfadumleitungen wählen.")
            ) from None
