"""Additive immutable geometry identities; no implied musical confirmation."""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from apps.archive.models import Record
from apps.archive.validation import bounded_json, reference
from core.page_geometry import SCHEMA, GeometryError, PageGeometry


class ImmutableRecord(Record):
    class Meta:
        abstract = True

    def clean(self):
        if not self._state.adding:
            raise ValidationError("Content revision history is immutable.")


class SourceDocument(ImmutableRecord):
    source_file = models.OneToOneField("archive.SourceFile", on_delete=models.PROTECT, related_name="document")


class PageRegion(ImmutableRecord):
    source_page = models.ForeignKey("archive.SourcePage", on_delete=models.PROTECT, related_name="regions")


class PageRegionRevision(ImmutableRecord):
    region = models.ForeignKey(PageRegion, on_delete=models.PROTECT, related_name="revisions")
    number = models.PositiveIntegerField()
    bounds_points = models.JSONField()
    geometry_schema = models.CharField(max_length=48, default=SCHEMA)
    page_fingerprint = models.CharField(max_length=64)
    transform_chain = models.JSONField(default=list, blank=True)

    def clean(self):
        super().clean()
        page = reference(reference(self, "region"), "source_page")
        if page.original_crop_box is None:
            raise ValidationError("Original source geometry must be inspected before defining regions.")
        if self.geometry_schema != SCHEMA or self.page_fingerprint != page.geometry_fingerprint:
            raise ValidationError("Region geometry must pin the exact source-page schema and fingerprint.")
        bounded_json(self.transform_chain, maximum=4096)
        # Canonical regions need no lossy display transforms. UI conversions are
        # calculated through DisplayTransform; unsupported transforms fail closed.
        if self.transform_chain != []:
            raise ValidationError("Only canonical PDF-point region coordinates are supported.")
        try:
            geometry = PageGeometry(page.media_box, page.original_crop_box, page.rotation, page.user_unit)
            self.bounds_points = list(geometry.region(self.bounds_points).bounds)
        except GeometryError as exc:
            raise ValidationError("Invalid canonical source region.") from exc

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["region", "number"], name="archive_region_revision_number"),
            models.CheckConstraint(condition=Q(number__gt=0), name="archive_region_revision_positive"),
        ]


class LogicalPage(ImmutableRecord):
    """Stable logical identity, independent of output paper size."""


class LogicalPageRevision(ImmutableRecord):
    logical_page = models.ForeignKey(LogicalPage, on_delete=models.PROTECT, related_name="revisions")
    number = models.PositiveIntegerField()
    source_page = models.ForeignKey("archive.SourcePage", on_delete=models.PROTECT, null=True, blank=True)
    region_revision = models.ForeignKey(PageRegionRevision, on_delete=models.PROTECT, null=True, blank=True)
    orientation = models.PositiveSmallIntegerField(default=0)
    content_bounds_points = models.JSONField(null=True, blank=True)

    def clean(self):
        super().clean()
        if (self.source_page_id is None) == (self.region_revision_id is None):
            raise ValidationError("A logical page pins exactly one complete source page or region revision.")
        if self.orientation not in (0, 90, 180, 270):
            raise ValidationError("Invalid logical orientation.")
        if self.region_revision_id:
            region = reference(self, "region_revision")
            bounds = region.bounds_points
        else:
            page = reference(self, "source_page")
            bounds = [float(value) * page.user_unit for value in page.effective_crop_box]
        if self.content_bounds_points is None:
            self.content_bounds_points = list(bounds)
        # Use the same canonical finite-positive/contained rectangle validator.
        try:
            geometry = PageGeometry(bounds, bounds)
            self.content_bounds_points = list(geometry.region(self.content_bounds_points).bounds)
        except GeometryError as exc:
            raise ValidationError("Invalid logical content bounds.") from exc

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["logical_page", "number"], name="archive_logical_revision_number"),
            models.CheckConstraint(condition=Q(number__gt=0), name="archive_logical_revision_positive"),
            models.CheckConstraint(
                condition=(
                    Q(source_page__isnull=False, region_revision__isnull=True)
                    | Q(source_page__isnull=True, region_revision__isnull=False)
                ),
                name="archive_logical_exact_input",
            ),
            models.CheckConstraint(condition=Q(orientation__in=[0, 90, 180, 270]), name="archive_logical_orientation"),
        ]


class ContentEdition(ImmutableRecord):
    arrangement = models.ForeignKey("catalog.Arrangement", on_delete=models.PROTECT)
    part = models.ForeignKey("catalog.Part", on_delete=models.PROTECT)


class ContentEditionRevision(ImmutableRecord):
    edition = models.ForeignKey(ContentEdition, on_delete=models.PROTECT, related_name="revisions")
    number = models.PositiveIntegerField()
    # Ordered, immutable proposal manifest. Relational pins are checked against it.
    manifest = models.JSONField()
    fingerprint = models.CharField(max_length=64)

    def clean(self):
        super().clean()
        from apps.archive.content_manifest import manifest_fingerprint

        if self.fingerprint != manifest_fingerprint(self.manifest):
            raise ValidationError("Content proposal fingerprint does not match its ordered manifest.")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["edition", "number"], name="archive_content_revision_number"),
            models.CheckConstraint(condition=Q(number__gt=0), name="archive_content_revision_positive"),
        ]


class ContentReference(ImmutableRecord):
    revision = models.ForeignKey(ContentEditionRevision, on_delete=models.PROTECT, related_name="references")
    sequence = models.PositiveIntegerField()
    logical_page_revision = models.ForeignKey(LogicalPageRevision, on_delete=models.PROTECT)
    archive_file = models.ForeignKey("archive.ArchiveFile", on_delete=models.PROTECT)
    file_revision = models.PositiveIntegerField()

    def clean(self):
        super().clean()
        self.validate_input()

    def validate_input(self):
        proposal = reference(self, "revision")
        logical = reference(self, "logical_page_revision")
        file = reference(self, "archive_file")
        page = logical.source_page if logical.source_page_id else logical.region_revision.region.source_page
        expected = {
            "occurrence_id": str(self.pk),
            "logical_page_revision_id": str(logical.pk),
            "archive_file_id": str(file.pk),
            "file_revision": self.file_revision,
        }
        if self.sequence >= len(proposal.manifest) or proposal.manifest[self.sequence] != expected:
            raise ValidationError("Content occurrence does not match its immutable proposal position.")
        if file.kind != "BASE" or file.source_version_id != page.source_version_id:
            raise ValidationError("Content references require the exact byte-identical source publication.")
        if file.revision != self.file_revision:
            raise ValidationError("Content publication changed.")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["revision", "sequence"], name="archive_content_sequence")]


class ContentInspection(ImmutableRecord):
    revision = models.ForeignKey(ContentEditionRevision, on_delete=models.PROTECT, related_name="inspections")
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fingerprint = models.CharField(max_length=64)
    visually_reviewed = models.BooleanField(default=False)

    def clean(self):
        super().clean()
        from apps.archive.content_services import _latest

        if self.visually_reviewed is not True or self.fingerprint != reference(self, "revision").fingerprint:
            raise ValidationError("Explicit visual review of the exact ordered content proposal is required.")
        if not reference(self, "reviewer").is_active:
            raise ValidationError("An active reviewer is required.")
        _latest(reference(self, "revision"), self._state.db or "default")


class ContentConfirmation(ImmutableRecord):
    inspection = models.OneToOneField(ContentInspection, on_delete=models.PROTECT, related_name="confirmation")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    def clean(self):
        super().clean()
        from apps.archive.content_services import _latest

        if self.actor_id != reference(self, "inspection").reviewer_id or not reference(self, "actor").is_active:
            raise ValidationError("Only the active inspecting reviewer can confirm this content revision.")
        _latest(reference(self, "inspection").revision, self._state.db or "default")
