"""Controlled project subset for inspection; not a personal full-folder list."""

from django import forms
from django.utils.translation import gettext_lazy as _


class PreflightSelection(forms.Form):
    participants = forms.MultipleChoiceField(label=_("Teilnehmende prüfen"), widget=forms.CheckboxSelectMultiple)
    positions = forms.MultipleChoiceField(label=_("Gemeinsame Positionen prüfen"), widget=forms.CheckboxSelectMultiple)

    def __init__(self, *args, project, **kwargs):
        super().__init__(*args, **kwargs)
        people = list(project.participants.filter(active=True).order_by("display_name", "pk")[:501])
        positions = list(
            project.positions.filter(active=True).select_related("arrangement__work").order_by("order")[:1001]
        )
        self.fields["participants"].choices = [(str(p.pk), p.display_name) for p in people]
        self.fields["positions"].choices = [
            (str(p.pk), f"{p.order}. {p.arrangement or _('Reserve')}") for p in positions
        ]
        if not self.is_bound:
            self.initial = {"participants": [str(p.pk) for p in people], "positions": [str(p.pk) for p in positions]}


class PreflightAcknowledgement(forms.Form):
    token = forms.CharField(max_length=4096, widget=forms.HiddenInput)
    acknowledgements = forms.MultipleChoiceField(
        required=False, widget=forms.CheckboxSelectMultiple, label=_("Fehlende Noten ausdrücklich bestätigen")
    )

    def __init__(self, *args, report, actor, **kwargs):
        from apps.projects.preflight_services import report_token

        super().__init__(*args, **kwargs)
        self.fields["acknowledgements"].choices = [
            (
                cell["key"],
                _("%(name)s · %(number)s. %(title)s — Noten fehlen; Platzhalter erforderlich")
                % {
                    "name": report.session.participants[cell["resolution"].participant_id].display_name,
                    "number": row["position"].order,
                    "title": row["position"].arrangement,
                },
            )
            for row in report.rows
            for cell in row["cells"]
            if cell["missing"]
        ]
        self.initial["token"] = report_token(report, actor)
