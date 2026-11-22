"""German reference-only ensemble controls scoped to the current project."""

from django import forms
from django.utils.translation import gettext_lazy as _

from apps.catalog.models import InstrumentVariant, Part
from apps.projects.forms import RevisionForm
from apps.projects.models import ProjectRole


class PositionChoice(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.order}. {obj.arrangement}"


class RoleForm(RevisionForm):
    code = forms.CharField(label=_("Rollenkürzel"), max_length=40)
    label = forms.CharField(label=_("Musikalische Rollenbezeichnung"), max_length=120, required=False)


class ParticipantRoleForm(RevisionForm):
    role = forms.ModelChoiceField(
        label=_("Musikalische Rolle"),
        queryset=ProjectRole.objects.none(),
        required=False,
        empty_label=_("Keine Rolle — gespeicherte Projektstimme"),
    )

    def __init__(self, *args, project, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].queryset = project.roles.filter(active=True).order_by("code_key", "pk")


class MappingForm(RevisionForm):
    role = forms.ModelChoiceField(label=_("Musikalische Rolle"), queryset=ProjectRole.objects.none())
    instrument = forms.ModelChoiceField(
        label=_("Spielbare Instrumentenvariante"), queryset=InstrumentVariant.objects.none()
    )
    part = forms.ModelChoiceField(label=_("Spielbare Stimme"), queryset=Part.objects.none())
    position = PositionChoice(
        label=_("Position (leer = Projektvorgabe)"), queryset=ProjectRole.objects.none(), required=False
    )

    def __init__(self, *args, project, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].queryset = project.roles.filter(active=True).order_by("code_key", "pk")
        self.fields["instrument"].queryset = InstrumentVariant.objects.filter(active=True).order_by(
            "name_key", "transposition_key", "clef", "pk"
        )
        self.fields["part"].queryset = (
            Part.objects.filter(active=True, instrument__active=True)
            .select_related("instrument")
            .order_by("instrument__name_key", "code_key", "pk")
        )
        self.fields["position"].queryset = (
            project.positions.filter(
                active=True, arrangement__isnull=False, arrangement__active=True, arrangement__work__active=True
            )
            .select_related("arrangement__work")
            .order_by("order")
        )

    def clean(self):
        values = super().clean()
        if values.get("part") and values.get("instrument") and values["part"].instrument_id != values["instrument"].pk:
            raise forms.ValidationError(_("Stimme passt nicht zur gewählten Stimmung und Notation."))
        return values
