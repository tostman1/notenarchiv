"""UUID catalog identities; names are descriptive and never implicit assignments."""

import re
import unicodedata
import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _


def normalized(value):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", "" if value is None else str(value)).strip()).casefold()


class Identity(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    revision = models.PositiveIntegerField(default=1, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    normalized_fields = {}

    class Meta:
        abstract = True

    def normalize(self):
        for target, source in self.normalized_fields.items():
            setattr(self, target, normalized(getattr(self, source)))

    def clean(self):
        self.normalize()
        for target, source in self.normalized_fields.items():
            if not self._meta.get_field(source).blank and not getattr(self, target):
                raise ValidationError({source: _("Bitte geben Sie eine nicht leere Bezeichnung ein.")})

    def full_clean(self, *args, **kwargs):
        self.normalize()
        return super().full_clean(*args, **kwargs)

    def save(self, *args, **kwargs):
        self.normalize()
        if kwargs.get("update_fields") is not None:
            kwargs["update_fields"] = set(kwargs["update_fields"]) | set(self.normalized_fields)
        return super().save(*args, **kwargs)


class ActiveIdentity(Identity):
    active = models.BooleanField(default=True, verbose_name=_("Aktiv"))

    class Meta:
        abstract = True


class Work(ActiveIdentity):
    title = models.CharField(max_length=200, verbose_name=_("Titel"))
    composer = models.CharField(max_length=160, blank=True, verbose_name=_("Komponist/in"))
    title_key = models.CharField(max_length=400, editable=False, db_index=True)
    composer_key = models.CharField(max_length=320, editable=False, blank=True)
    normalized_fields = {"title_key": "title", "composer_key": "composer"}

    def __str__(self):
        label = f"{self.title} · {self.composer or '—'} · {str(self.pk)[:8]}"
        return label if self.active else label + str(_(" (inaktiv)"))


class Arrangement(ActiveIdentity):
    work = models.ForeignKey(Work, on_delete=models.PROTECT, related_name="arrangements", verbose_name=_("Werk"))
    arranger = models.CharField(max_length=160, blank=True, verbose_name=_("Arrangeur/in"))
    edition = models.CharField(max_length=160, blank=True, verbose_name=_("Ausgabe / Bezeichnung"))
    expectations_defined = models.BooleanField(default=False, verbose_name=_("Erwartete Besetzung ist festgelegt"))
    arranger_key = models.CharField(max_length=320, blank=True, editable=False)
    edition_key = models.CharField(max_length=320, blank=True, editable=False)
    normalized_fields = {"arranger_key": "arranger", "edition_key": "edition"}

    def __str__(self):
        label = f"{self.work.title} · {self.arranger or '—'} · {self.edition or '—'} · {str(self.pk)[:8]}"
        return label if self.active else label + str(_(" (inaktiv)"))


class InstrumentVariant(ActiveIdentity):
    class Clef(models.TextChoices):
        TREBLE = "TREBLE", _("Violinschlüssel")
        BASS = "BASS", _("Bassschlüssel")
        ALTO = "ALTO", _("Altschlüssel")
        TENOR = "TENOR", _("Tenorschlüssel")
        PERCUSSION = "PERCUSSION", _("Schlagzeugnotation")

    name = models.CharField(max_length=120, verbose_name=_("Instrument"))
    family = models.CharField(max_length=120, blank=True, verbose_name=_("Instrumentenfamilie"))
    transposition = models.CharField(max_length=40, default="C", verbose_name=_("Stimmung / Transposition"))
    clef = models.CharField(max_length=16, choices=Clef, default=Clef.TREBLE, verbose_name=_("Notation / Schlüssel"))
    name_key = models.CharField(max_length=240, editable=False)
    family_key = models.CharField(max_length=240, blank=True, editable=False)
    transposition_key = models.CharField(max_length=80, editable=False)
    normalized_fields = {"name_key": "name", "family_key": "family", "transposition_key": "transposition"}

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name_key", "family_key", "transposition_key", "clef"],
                name="catalog_unique_variant",
                violation_error_message=_("Diese Instrumentenvariante ist bereits vorhanden."),
            )
        ]

    def __str__(self):
        label = f"{self.name} · {self.transposition} · {self.get_clef_display()} · {self.family or '—'}"
        return label if self.active else label + str(_(" (inaktiv)"))


class Part(ActiveIdentity):
    instrument = models.ForeignKey(
        InstrumentVariant, on_delete=models.PROTECT, related_name="parts", verbose_name=_("Instrumentenvariante")
    )
    code = models.CharField(max_length=40, verbose_name=_("Stimmennummer / Kürzel"))
    label = models.CharField(max_length=120, blank=True, verbose_name=_("Bezeichnung"))
    code_key = models.CharField(max_length=80, editable=False)
    label_key = models.CharField(max_length=240, blank=True, editable=False)
    normalized_fields = {"code_key": "code", "label_key": "label"}

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["instrument", "code_key"],
                name="catalog_unique_part",
                violation_error_message=_("Diese Stimme ist für die Instrumentenvariante bereits vorhanden."),
            )
        ]

    def __str__(self):
        label = f"{self.instrument} · {self.code}" + (f" ({self.label})" if self.label else "")
        return label if self.active else label + str(_(" (inaktiv)"))


class WorkAlias(ActiveIdentity):
    work = models.ForeignKey(Work, on_delete=models.PROTECT, related_name="aliases", verbose_name=_("Werk"))
    alias = models.CharField(max_length=200, verbose_name=_("Alias"))
    alias_key = models.CharField(max_length=400, editable=False)
    normalized_fields = {"alias_key": "alias"}

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["work", "alias_key"],
                name="catalog_unique_work_alias",
                violation_error_message=_("Dieser Alias ist dem Werk bereits zugeordnet."),
            )
        ]

    def __str__(self):
        return f"{self.alias} → {self.work}"


class InstrumentAlias(ActiveIdentity):
    alias = models.CharField(max_length=120, verbose_name=_("Alias"))
    alias_key = models.CharField(max_length=240, editable=False)
    instrument = models.ForeignKey(
        InstrumentVariant,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="aliases",
        verbose_name=_("Instrumentenvariante"),
    )
    part = models.ForeignKey(
        Part, on_delete=models.PROTECT, null=True, blank=True, related_name="aliases", verbose_name=_("Stimme")
    )
    normalized_fields = {"alias_key": "alias"}

    def clean(self):
        super().clean()
        if bool(self.instrument_id) == bool(self.part_id):
            raise ValidationError(_("Wählen Sie genau eine Instrumentenvariante oder eine Stimme."))

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(Q(instrument__isnull=False) & Q(part__isnull=True))
                | (Q(instrument__isnull=True) & Q(part__isnull=False)),
                name="catalog_alias_one_target",
            ),
            models.UniqueConstraint(
                fields=["alias_key", "instrument"],
                condition=Q(instrument__isnull=False),
                name="catalog_unique_instrument_alias",
                violation_error_message=_("Dieser Alias ist der Variante bereits zugeordnet."),
            ),
            models.UniqueConstraint(
                fields=["alias_key", "part"],
                condition=Q(part__isnull=False),
                name="catalog_unique_part_alias",
                violation_error_message=_("Dieser Alias ist der Stimme bereits zugeordnet."),
            ),
        ]

    def __str__(self):
        return f"{self.alias} → {self.instrument or self.part}"


class ExpectedPart(Identity):
    arrangement = models.ForeignKey(
        Arrangement, on_delete=models.PROTECT, related_name="expected_parts", verbose_name=_("Arrangement")
    )
    part = models.ForeignKey(Part, on_delete=models.PROTECT, related_name="expectations", verbose_name=_("Stimme"))
    required = models.BooleanField(default=True, verbose_name=_("Erforderlich (sonst optional)"))

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["arrangement", "part"],
                name="catalog_unique_expectation",
                violation_error_message=_("Diese Stimme ist bereits in der Erwartungsliste enthalten."),
            )
        ]

    def __str__(self):
        return f"{self.arrangement} → {self.part}"


class InstrumentationTemplate(ActiveIdentity):
    name = models.CharField(max_length=160, verbose_name=_("Vorlagenname"))
    name_key = models.CharField(max_length=320, editable=False, db_index=True)
    normalized_fields = {"name_key": "name"}

    def __str__(self):
        return f"{self.name} · {str(self.pk)[:8]}"


class TemplatePart(Identity):
    template = models.ForeignKey(
        InstrumentationTemplate, on_delete=models.PROTECT, related_name="entries", verbose_name=_("Besetzungsvorlage")
    )
    part = models.ForeignKey(Part, on_delete=models.PROTECT, related_name="template_entries", verbose_name=_("Stimme"))
    required = models.BooleanField(default=True, verbose_name=_("Erforderlich (sonst optional)"))

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["template", "part"],
                name="catalog_unique_template_part",
                violation_error_message=_("Diese Stimme ist bereits in der Vorlage enthalten."),
            )
        ]

    def __str__(self):
        return f"{self.template} → {self.part}"
