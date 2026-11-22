"""Controlled German rule references, never free-text musical assignments."""

from django import forms
from django.utils.translation import gettext_lazy as _

from apps.archive.models import ArchiveAssignment
from apps.catalog.models import Arrangement, Part
from apps.projects.ensemble_forms import PositionChoice
from apps.projects.forms import RevisionForm
from apps.projects.models import ProjectPosition


class ReplacementForm(RevisionForm):
    desired_part = forms.ModelChoiceField(label=_("Gewünschte spielbare Stimme"), queryset=Part.objects.none())
    replacement_part = forms.ModelChoiceField(label=_("Explizite Ersatzstimme"), queryset=Part.objects.none())
    position = PositionChoice(
        label=_("Position (leer = Projektvorgabe)"), queryset=ProjectPosition.objects.none(), required=False
    )

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        parts = (
            Part.objects.filter(active=True, instrument__active=True)
            .select_related("instrument")
            .order_by("instrument__name_key", "code_key", "pk")
        )
        self.fields["desired_part"].queryset = parts
        self.fields["replacement_part"].queryset = parts
        if project is None:
            self.fields.pop("position")
        else:
            self.fields["position"].queryset = project.positions.filter(
                active=True, arrangement__isnull=False, arrangement__active=True, arrangement__work__active=True
            ).select_related("arrangement__work")


class EditionForm(RevisionForm):
    arrangement = forms.ModelChoiceField(label=_("Arrangement"), queryset=Arrangement.objects.none())
    part = forms.ModelChoiceField(label=_("Spielbare Stimme"), queryset=Part.objects.none())
    edition = forms.ModelChoiceField(label=_("Konkrete bestätigte Ausgabe"), queryset=ArchiveAssignment.objects.none())
    position = PositionChoice(
        label=_("Position (leer = Projektvorgabe)"), queryset=ProjectPosition.objects.none(), required=False
    )

    def __init__(self, *args, project, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["arrangement"].queryset = (
            Arrangement.objects.filter(active=True, work__active=True)
            .select_related("work")
            .order_by("work__title_key", "pk")
        )
        self.fields["part"].queryset = (
            Part.objects.filter(active=True, instrument__active=True)
            .select_related("instrument")
            .order_by("instrument__name_key", "code_key", "pk")
        )
        self.fields["edition"].queryset = (
            ArchiveAssignment.objects.usable()
            .select_related("archive_file__arrangement__work", "part__instrument")
            .order_by("pk")
        )
        self.fields["edition"].label_from_instance = (
            lambda row: f"{row.archive_file.arrangement} · {row.part} · {row.archive_file.pk}"
        )
        self.fields["position"].queryset = project.positions.filter(
            active=True, arrangement__isnull=False, arrangement__active=True, arrangement__work__active=True
        ).select_related("arrangement__work")

    def clean(self):
        values = super().clean()
        edition, part, arrangement = (values.get(name) for name in ("edition", "part", "arrangement"))
        if (
            edition
            and part
            and arrangement
            and (edition.part_id != part.pk or edition.archive_file.arrangement_id != arrangement.pk)
        ):
            raise forms.ValidationError(_("Ausgabe passt nicht zum exakten Arrangement und zur spielbaren Stimme."))
        if values.get("position") and arrangement and values["position"].arrangement_id != arrangement.pk:
            raise forms.ValidationError(_("Position gehört zu einem anderen Arrangement."))
        return values
