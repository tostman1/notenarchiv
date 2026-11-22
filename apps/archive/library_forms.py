"""Controlled German library search, separate review and expectation filters."""

from django import forms
from django.utils.translation import gettext_lazy as _

from apps.catalog.models import Arrangement, InstrumentVariant, Part


class LibraryFilters(forms.Form):
    q = forms.CharField(label=_("Titel oder Alias"), max_length=200, required=False)
    arrangement = forms.ModelChoiceField(label=_("Arrangement"), queryset=Arrangement.objects.none(), required=False)
    instrument = forms.ModelChoiceField(
        label=_("Instrumentenvariante"), queryset=InstrumentVariant.objects.none(), required=False
    )
    part = forms.ModelChoiceField(label=_("Stimme"), queryset=Part.objects.none(), required=False)
    review = forms.ChoiceField(
        label=_("Archivmaterial"),
        required=False,
        choices=[
            ("", _("Alle")),
            ("CONFIRMED", _("Bestätigte verfügbare Versionen")),
            ("PENDING", _("Ungeprüfte Versionen")),
            ("UNCERTAIN", _("Unklare oder widersprüchliche Erkennung")),
        ],
    )
    completeness = forms.ChoiceField(
        label=_("Vollständigkeit laut Archivstatus"),
        required=False,
        choices=[
            ("", _("Alle")),
            ("UNKNOWN", _("Erwartung unbekannt")),
            ("COMPLETE", _("Erforderliche Stimmen bestätigt")),
            ("INCOMPLETE", _("Erforderliche Stimmen fehlen oder sind ungeprüft")),
            ("NOT_REQUIRED", _("Keine erforderlichen Stimmen festgelegt")),
        ],
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["arrangement"].queryset = (
            Arrangement.objects.filter(active=True, work__active=True)
            .select_related("work")
            .order_by("work__title_key", "arranger_key", "edition_key", "pk")
        )
        self.fields["instrument"].queryset = InstrumentVariant.objects.filter(active=True).order_by(
            "name_key", "transposition_key", "clef", "pk"
        )
        self.fields["part"].queryset = (
            Part.objects.filter(active=True, instrument__active=True)
            .select_related("instrument")
            .order_by("instrument__name_key", "code_key", "pk")
        )

    def clean(self):
        values = super().clean()
        if values.get("instrument") and values.get("part") and values["part"].instrument_id != values["instrument"].pk:
            raise forms.ValidationError(_("Die Stimme gehört nicht zur gewählten Instrumentenvariante."))
        return values
