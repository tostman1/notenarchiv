"""Bounded matrix navigation parameters; never mutate project selection."""

from django import forms
from django.utils.translation import gettext_lazy as _

from apps.catalog.models import InstrumentVariant


class MatrixFilters(forms.Form):
    q = forms.CharField(label=_("Teilnehmende suchen"), required=False, max_length=160)
    participant = forms.UUIDField(label=_("Teilnehmende"), required=False, widget=forms.Select)
    instrument = forms.UUIDField(label=_("Instrumentenvariante"), required=False, widget=forms.Select)
    deviation = forms.ChoiceField(
        label=_("Abweichungen"),
        required=False,
        choices=[
            ("", _("Alle Zuordnungen")),
            ("personal", _("Persönliche Overrides")),
            ("issues", _("Fehlend oder ungeklärt")),
            ("deviations", _("Abweichung vom Projektdefault")),
        ],
    )

    def __init__(self, *args, project, **kwargs):
        super().__init__(*args, **kwargs)
        people = list(
            project.participants.filter(active=True)
            .order_by("display_name", "pk")
            .values_list("pk", "display_name", "default_part__instrument_id")[:501]
        )
        self.fields["participant"].widget.choices = [
            ("", _("Alle Teilnehmenden")),
            *[(pk, name) for pk, name, _ in people],
        ]
        self.fields["instrument"].widget.choices = [
            ("", _("Alle Instrumentenvarianten")),
            *[
                (item.pk, str(item))
                for item in InstrumentVariant.objects.filter(pk__in={row[2] for row in people}).order_by(
                    "name_key", "transposition_key", "clef"
                )
            ],
        ]


def navigation_values(data):
    """Only allow bounded view state through GET/POST navigation, not business input."""
    return {
        key: str(data.get(key, ""))[:160] for key in ("q", "participant", "instrument", "deviation") if data.get(key)
    }
