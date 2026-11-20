"""Validated, finite diagnostic filters; no filesystem paths are accepted."""

from django import forms
from django.utils.translation import gettext_lazy as _

from apps.jobs.presentation import KINDS, STATUSES
from apps.jobs.services.diagnostics import LEVELS, SOURCES
from config.diagnostics import COMPONENTS


class DiagnosticFilters(forms.Form):
    source = forms.ChoiceField(label=_("Dienst"), choices=[(source, source) for source in SOURCES], initial="web")
    level = forms.ChoiceField(
        label=_("Stufe"), choices=[("", _("Alle"))] + [(level, level) for level in LEVELS], required=False
    )
    component = forms.ChoiceField(
        label=_("Komponente"),
        choices=[("", _("Alle"))] + [(name, name) for name in sorted(COMPONENTS | {"application", "django"})],
        required=False,
    )
    job_id = forms.UUIDField(label=_("Auftrags-ID"), required=False)
    since = forms.DateTimeField(
        label=_("Von"), required=False, widget=forms.DateTimeInput(attrs={"type": "datetime-local"})
    )
    until = forms.DateTimeField(
        label=_("Bis"), required=False, widget=forms.DateTimeInput(attrs={"type": "datetime-local"})
    )
    history = forms.BooleanField(label=_("Ab ältester gespeicherter Meldung lesen"), required=False)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("since") and cleaned.get("until") and cleaned["since"] > cleaned["until"]:
            raise forms.ValidationError(_("Der Beginn muss vor dem Ende liegen."))
        return cleaned


class JobFilters(forms.Form):
    status = forms.ChoiceField(label=_("Status"), choices=[("", _("Alle")), *STATUSES.items()], required=False)
    kind = forms.ChoiceField(label=_("Auftragsart"), choices=[("", _("Alle")), *KINDS.items()], required=False)
