"""Collections are independent of composition hierarchy and title identity."""

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from apps.catalog.models import ActiveIdentity, Identity

METADATA_FIELDS = frozenset(
    {"publisher", "edition", "identifier", "physical_format", "composer", "arranger", "section"}
)


def validate_metadata(value):
    if not isinstance(value, dict) or set(value) - METADATA_FIELDS:
        raise ValidationError("Unsupported collection metadata fields.")
    if any(not isinstance(item, str) or len(item) > 200 for item in value.values()):
        raise ValidationError("Metadata values must be bounded text.")


class ValidatedIdentity(Identity):
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self._state.db = kwargs.get("using") or self._state.db or "default"
        self.full_clean()
        return super().save(*args, **kwargs)


class RetainedIdentity(ValidatedIdentity):
    class Meta:
        abstract = True

    def clean(self):
        super().clean()
        if not self._state.adding:
            raise ValidationError("Catalog association history is immutable.")

    def delete(self, *args, **kwargs):
        raise ValidationError("Catalog association history is retained.")


class Collection(ActiveIdentity):
    title = models.CharField(max_length=200, verbose_name=_("Sammlung"))
    title_key = models.CharField(max_length=400, editable=False, db_index=True)
    instrument = models.ForeignKey("catalog.InstrumentVariant", null=True, blank=True, on_delete=models.PROTECT)
    metadata = models.JSONField(default=dict, blank=True, validators=[validate_metadata])
    normalized_fields = {"title_key": "title"}

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class CollectionMembership(RetainedIdentity):
    collection = models.ForeignKey(Collection, on_delete=models.PROTECT, related_name="memberships")
    work = models.ForeignKey("catalog.Work", on_delete=models.PROTECT, related_name="collection_memberships")
    position = models.PositiveIntegerField()
    original_song_number = models.CharField(max_length=80, blank=True)
    local_overrides = models.JSONField(default=dict, blank=True, validators=[validate_metadata])
    metadata_snapshot = models.JSONField()

    def clean(self):
        super().clean()
        from apps.catalog.collection_services import metadata_snapshot

        if self.metadata_snapshot != metadata_snapshot(self.collection, self.work, self.local_overrides):
            raise ValidationError("Collection membership requires an exact provenance snapshot.")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["collection", "position"], name="catalog_collection_position")]


class WorkRelationship(RetainedIdentity):
    class Kind(models.TextChoices):
        MOVEMENT = "MOVEMENT", _("Satz / Abschnitt")
        MEDLEY = "MEDLEY", _("Medley-Bestandteil")
        RELATED = "RELATED", _("Verwandte Bearbeitung / Ausgabe")

    parent = models.ForeignKey("catalog.Work", on_delete=models.PROTECT, related_name="component_relationships")
    component = models.ForeignKey("catalog.Work", on_delete=models.PROTECT, related_name="parent_relationships")
    kind = models.CharField(max_length=16, choices=Kind.choices)
    position = models.PositiveIntegerField()
    parent_arrangement = models.ForeignKey(
        "catalog.Arrangement", null=True, blank=True, on_delete=models.PROTECT, related_name="related_components"
    )
    component_arrangement = models.ForeignKey(
        "catalog.Arrangement", null=True, blank=True, on_delete=models.PROTECT, related_name="related_parents"
    )

    def clean(self):
        super().clean()
        from apps.catalog.collection_services import validate_relationship

        validate_relationship(self, using=self._state.db or "default")

    class Meta:
        constraints = [
            models.CheckConstraint(condition=~Q(parent=models.F("component")), name="catalog_relationship_not_self"),
            models.UniqueConstraint(fields=["parent", "kind", "position"], name="catalog_relationship_position"),
        ]


class WorkAlternativeTitle(RetainedIdentity):
    work = models.ForeignKey("catalog.Work", on_delete=models.PROTECT, related_name="alternative_titles")
    title = models.CharField(max_length=200, verbose_name=_("Alternativer Titel"))
    title_key = models.CharField(max_length=400, editable=False, db_index=True)
    normalized_fields = {"title_key": "title"}
