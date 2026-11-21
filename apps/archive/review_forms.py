"""German review forms bound to a file version, proposal and optimistic revision."""

from django import forms
from django.utils.translation import gettext_lazy as _

from apps.catalog.models import Arrangement, InstrumentVariant, Part


class VersionForm(forms.Form):
    expected_revision = forms.IntegerField(min_value=1, widget=forms.HiddenInput)
    source_version = forms.UUIDField(widget=forms.HiddenInput)
    sha256 = forms.RegexField(r"\A[0-9a-f]{64}\Z", widget=forms.HiddenInput)
    proposal = forms.UUIDField(required=False, widget=forms.HiddenInput)


class CorrectionForm(VersionForm):
    arrangement = forms.ModelChoiceField(label=_("Arrangement / Ausgabe"), queryset=Arrangement.objects.none())
    instruments = forms.ModelMultipleChoiceField(
        label=_("Instrumentenvarianten (Mehrfachauswahl)"),
        queryset=InstrumentVariant.objects.none(),
        help_text=_("Stimmung und Notation beachten. Für kombinierte PDFs mehrere Varianten wählen."),
    )
    parts = forms.ModelMultipleChoiceField(
        label=_("Musikalische Stimmen (Mehrfachauswahl)"),
        queryset=Part.objects.none(),
        help_text=_("Alle enthaltenen Stimmen auswählen. Eine kombinierte PDF wird nicht geteilt."),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["arrangement"].queryset = (
            Arrangement.objects.filter(active=True, work__active=True)
            .select_related("work")
            .order_by("work__title_key", "arranger_key", "edition_key", "pk")
        )
        self.fields["instruments"].queryset = InstrumentVariant.objects.filter(active=True).order_by(
            "name_key", "transposition_key", "clef", "pk"
        )
        self.fields["parts"].queryset = (
            Part.objects.filter(active=True, instrument__active=True)
            .select_related("instrument")
            .order_by("instrument__name_key", "instrument__transposition_key", "instrument__clef", "code_key")
        )

    def clean(self):
        cleaned = super().clean()
        if "instruments" in cleaned and "parts" in cleaned:
            selected = {instrument.pk for instrument in cleaned["instruments"]}
            actual = {part.instrument_id for part in cleaned["parts"]}
            if selected != actual:
                raise forms.ValidationError(
                    _("Die gewählten Stimmen müssen genau zu den gewählten Instrumentenvarianten gehören.")
                )
        return cleaned


class InspectionForm(VersionForm):
    explicit = forms.BooleanField(
        label=_("Ich habe alle Seiten dieser Version visuell geprüft und die gespeicherte Zuordnung kontrolliert")
    )


class ApprovalForm(VersionForm):
    explicit = forms.BooleanField(label=_("Diese von mir visuell geprüfte Zuordnung ausdrücklich freigeben"))


class RejectionForm(VersionForm):
    explicit = forms.BooleanField(
        label=_("Gespeicherten Zuordnungsvorschlag verwerfen (PDF und Historie bleiben erhalten)")
    )
