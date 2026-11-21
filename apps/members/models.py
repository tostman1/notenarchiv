"""Members have stable identities and exactly one protected regular part."""

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.catalog.models import ActiveIdentity, Part


class Member(ActiveIdentity):
    name = models.CharField(max_length=160, verbose_name=_("Name"))
    membership_id = models.CharField(max_length=80, blank=True, verbose_name=_("Mitgliedsnummer (optional)"))
    regular_part = models.ForeignKey(
        Part, on_delete=models.PROTECT, related_name="regular_members", verbose_name=_("Stammstimme")
    )
    name_key = models.CharField(max_length=320, editable=False, db_index=True)
    membership_key = models.CharField(max_length=160, blank=True, editable=False)
    normalized_fields = {"name_key": "name", "membership_key": "membership_id"}

    def clean(self):
        super().clean()
        if self.active and self.regular_part_id:
            try:
                part = (
                    Part.objects.using(self._state.db or "default")
                    .select_related("instrument")
                    .get(pk=self.regular_part_id)
                )
            except (Part.DoesNotExist, ValidationError):
                return  # Foreign-key field validation reports the invalid reference.
            if not part.active or not part.instrument.active:
                raise ValidationError(
                    {"regular_part": _("Aktive Mitglieder benötigen eine aktive Stammstimme und Instrumentenvariante.")}
                )

    def __str__(self):
        return f"{self.name} · {self.membership_id or '—'} · {str(self.pk)[:8]}"
