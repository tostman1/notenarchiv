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


class RegionRevisionForm(forms.Form):
    expected_file_revision = forms.IntegerField(min_value=1, widget=forms.HiddenInput)
    source_version_id = forms.UUIDField(widget=forms.HiddenInput)
    region_id = forms.UUIDField(required=False, widget=forms.HiddenInput)
    expected_region_number = forms.IntegerField(min_value=0, widget=forms.HiddenInput, initial=0)


class ContentEditionCreationForm(forms.Form):
    arrangement = forms.ModelChoiceField(label=_("Arrangement / Ausgabe"), queryset=Arrangement.objects.none())
    part = forms.ModelChoiceField(label=_("Musikalische Stimme"), queryset=Part.objects.none())
    explicit = forms.BooleanField(
        label=_("Neue eigenständige Inhaltsausgabe für dieses Arrangement und diese Stimme anlegen")
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["arrangement"].queryset = (
            Arrangement.objects.filter(active=True, work__active=True)
            .select_related("work")
            .order_by("work__title_key", "arranger_key", "edition_key", "pk")
        )
        self.fields["part"].queryset = (
            Part.objects.filter(active=True, instrument__active=True)
            .select_related("instrument")
            .order_by("instrument__name_key", "instrument__transposition_key", "instrument__clef", "code_key")
        )


class RegionContentForm(forms.Form):
    edition = forms.ModelChoiceField(label=_("Musikalische Inhaltsausgabe"), queryset=Arrangement.objects.none())
    expected_edition_number = forms.IntegerField(
        label=_("Aktuelle Vorschlagsrevision (0 bei neuer Ausgabe)"), min_value=0, initial=0
    )
    expected_file_revision = forms.IntegerField(min_value=1, widget=forms.HiddenInput)
    source_version_id = forms.UUIDField(widget=forms.HiddenInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.db.models import Max

        from apps.archive import models as m

        self.fields["edition"].queryset = (
            m.ContentEdition.objects.filter(
                arrangement__active=True,
                arrangement__work__active=True,
                part__active=True,
                part__instrument__active=True,
            )
            .select_related("arrangement__work", "part__instrument")
            .annotate(current_number=Max("revisions__number"))
            .order_by("arrangement__work__title_key", "pk")
        )
        self.fields["edition"].label_from_instance = lambda edition: (
            f"{edition.arrangement} / {edition.part} (Revision {edition.current_number or 0})"
        )


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


class OcrSelectionForm(forms.Form):
    """Optional localized OCR region as percentages of the displayed page.

    This is evidence collection only; it never approves or reassigns a version.
    """

    page = forms.IntegerField(
        label=_("Seite (1 = erste Seite)"),
        min_value=1,
        max_value=500,
        initial=1,
        help_text=_("Seitennummer der PDF, auf der der markierte Bereich liegt."),
        widget=forms.NumberInput(attrs={"min": "1", "max": "500", "step": "1"}),
    )
    left = forms.FloatField(
        label=_("Linke Kante"),
        min_value=0,
        max_value=100,
        initial=0,
        help_text=_("Linke Kante in % der Seitenbreite (0–100), kleiner als rechte Kante."),
        widget=forms.NumberInput(attrs={"min": "0", "max": "100", "step": "any"}),
    )
    top = forms.FloatField(
        label=_("Obere Kante"),
        min_value=0,
        max_value=100,
        initial=0,
        help_text=_("Obere Kante in % der Seitenhöhe (0–100), kleiner als untere Kante."),
        widget=forms.NumberInput(attrs={"min": "0", "max": "100", "step": "any"}),
    )
    right = forms.FloatField(
        label=_("Rechte Kante"),
        min_value=0,
        max_value=100,
        initial=100,
        help_text=_("Rechte Kante in % der Seitenbreite (0–100), größer als linke Kante."),
        widget=forms.NumberInput(attrs={"min": "0", "max": "100", "step": "any"}),
    )
    bottom = forms.FloatField(
        label=_("Untere Kante"),
        min_value=0,
        max_value=100,
        initial=100,
        help_text=_("Untere Kante in % der Seitenhöhe (0–100), größer als obere Kante."),
        widget=forms.NumberInput(attrs={"min": "0", "max": "100", "step": "any"}),
    )

    def clean(self):
        cleaned = super().clean()
        left, right = cleaned.get("left"), cleaned.get("right")
        top, bottom = cleaned.get("top"), cleaned.get("bottom")
        if left is not None and right is not None and left >= right:
            raise forms.ValidationError(_("Die linke Kante muss kleiner als die rechte Kante sein."))
        if top is not None and bottom is not None and top >= bottom:
            raise forms.ValidationError(_("Die obere Kante muss kleiner als die untere Kante sein."))
        return cleaned
