"""Immutable authorization payloads and relational exact-version pins."""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class ImmutableQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError("Generation authorization records are immutable.")

    def delete(self):
        raise ValidationError("Generation authorization history is retained.")


class ImmutableRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    objects = ImmutableQuerySet.as_manager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Generation authorization records are immutable.")
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Generation authorization history is retained.")


class GenerationSnapshot(ImmutableRecord):
    request_id = models.UUIDField(unique=True, default=uuid.uuid4)
    project = models.ForeignKey("projects.Project", on_delete=models.PROTECT)
    project_revision = models.PositiveBigIntegerField()
    kind = models.CharField(max_length=16, choices=[("FULL", "FULL"), ("EXCERPT", "EXCERPT"), ("CONTENTS", "CONTENTS")])
    payload = models.JSONField()
    sha256 = models.CharField(max_length=64)
    preflight_sha256 = models.CharField(max_length=64)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    acknowledgements = models.JSONField(default=list, blank=True)

    def clean(self):
        from apps.projects.preflight_services import fingerprint

        if not isinstance(self.payload, dict) or len(str(self.payload)) > 8 * 1024**2:
            raise ValidationError("Snapshot payload is invalid or exceeds its bound.")
        if self.sha256 != fingerprint(self.payload) or self.payload.get("blocking") != 0:
            raise ValidationError("Snapshot must match a verified nonblocking report.")
        if self.payload.get("project") != str(self.project_id) or self.payload.get("revision") != self.project_revision:
            raise ValidationError("Snapshot project revision must match its canonical payload.")
        missing = {
            f"{cell['position_id']}:{cell['participant_id']}"
            for cell in self.payload.get("cells", [])
            if cell["status"] == "MISSING"
        }
        if set(self.acknowledgements) != missing or len(self.acknowledgements) != len(missing):
            raise ValidationError("Snapshot missing decisions must match every requested missing cell.")


class GenerationRun(ImmutableRecord):
    snapshot = models.OneToOneField(GenerationSnapshot, on_delete=models.PROTECT, related_name="run")
    job = models.OneToOneField("jobs.Job", on_delete=models.PROTECT, related_name="generation_run")

    def clean(self):
        if self.job.kind != "GENERATE" or self.job.payload != {
            "snapshot_id": str(self.snapshot_id),
            "sha256": self.snapshot.sha256,
        }:
            raise ValidationError("Generation run must bind its exact authorized job.")


class SnapshotParticipant(ImmutableRecord):
    snapshot = models.ForeignKey(GenerationSnapshot, on_delete=models.PROTECT, related_name="participants")
    participant = models.ForeignKey("projects.ProjectParticipant", on_delete=models.PROTECT)
    default_part = models.ForeignKey("catalog.Part", on_delete=models.PROTECT)
    role = models.ForeignKey("projects.ProjectRole", on_delete=models.PROTECT, null=True, blank=True)
    display_name = models.CharField(max_length=160)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["snapshot", "participant"], name="exports_unique_person_pin")]

    def clean(self):
        if self.participant.project_id != self.snapshot.project_id:
            raise ValidationError("Pinned participant belongs to another project.")


class SnapshotPosition(ImmutableRecord):
    snapshot = models.ForeignKey(GenerationSnapshot, on_delete=models.PROTECT, related_name="positions")
    position = models.ForeignKey("projects.ProjectPosition", on_delete=models.PROTECT)
    arrangement = models.ForeignKey("catalog.Arrangement", on_delete=models.PROTECT, null=True, blank=True)
    number = models.PositiveIntegerField()
    title = models.CharField(max_length=1000)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["snapshot", "position"], name="exports_unique_position_pin"),
            models.UniqueConstraint(fields=["snapshot", "number"], name="exports_unique_number_pin"),
        ]

    def clean(self):
        if self.position.project_id != self.snapshot.project_id:
            raise ValidationError("Pinned position belongs to another project.")


class SnapshotInput(ImmutableRecord):
    snapshot = models.ForeignKey(GenerationSnapshot, on_delete=models.PROTECT, related_name="inputs")
    position = models.ForeignKey("projects.ProjectPosition", on_delete=models.PROTECT)
    participant = models.ForeignKey("projects.ProjectParticipant", on_delete=models.PROTECT)
    part = models.ForeignKey("catalog.Part", on_delete=models.PROTECT)
    assignment = models.ForeignKey("archive.ArchiveAssignment", on_delete=models.PROTECT)
    archive_file = models.ForeignKey("archive.ArchiveFile", on_delete=models.PROTECT)
    source_version = models.ForeignKey("archive.SourceVersion", on_delete=models.PROTECT)
    sha256 = models.CharField(max_length=64)
    byte_size = models.PositiveBigIntegerField()
    file_revision = models.PositiveBigIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["snapshot", "position", "participant"], name="exports_unique_cell_pin")
        ]

    def clean(self):
        if (
            self.position.project_id != self.snapshot.project_id
            or self.participant.project_id != self.snapshot.project_id
        ):
            raise ValidationError("Pinned cell belongs to another project.")
        if (
            self.assignment.archive_file_id != self.archive_file_id
            or self.assignment.part_id != self.part_id
            or self.archive_file.source_version_id != self.source_version_id
            or self.archive_file.sha256 != self.sha256
            or self.archive_file.byte_size != self.byte_size
        ):
            raise ValidationError("Pinned input identity does not match its source.")
