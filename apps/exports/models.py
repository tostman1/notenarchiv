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
    source_snapshot = models.ForeignKey("self", on_delete=models.PROTECT, null=True, blank=True)
    request_id = models.UUIDField(unique=True, default=uuid.uuid4)
    project = models.ForeignKey("projects.Project", on_delete=models.PROTECT, null=True, blank=True)
    project_revision = models.PositiveBigIntegerField()
    kind = models.CharField(
        max_length=16,
        choices=[
            ("FULL", "FULL"),
            ("EXCERPT", "EXCERPT"),
            ("CONTENTS", "CONTENTS"),
            ("ARCHIVE_NOTES", "ARCHIVE_NOTES"),
        ],
    )
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
        if self.kind == "CONTENTS" and (self.payload.get("participants") or self.payload.get("cells")):
            raise ValidationError("Contents snapshots cannot contain personal musical inputs.")
        if (self.kind == "ARCHIVE_NOTES") != (self.project_id is None):
            raise ValidationError("Only archive-note snapshots may omit a project.")
        if self.kind == "ARCHIVE_NOTES" and (
            self.payload.get("positions") or self.payload.get("participants") or self.payload.get("cells")
        ):
            raise ValidationError("Archive-note snapshots cannot contain project identities.")
        if self.source_snapshot_id:
            if self.payload.get("output_variant") == "PRINT":
                source = dict(self.source_snapshot.payload)
                source["output_variant"] = "PRINT"
                if source != self.payload or self.kind != self.source_snapshot.kind:
                    raise ValidationError("Print run must preserve its exact source snapshot.")
                return
            if self.kind != "EXCERPT" or self.source_snapshot.project_id != self.project_id:
                raise ValidationError("Historical excerpt provenance must refer to the same project.")
            if self.payload.get("historical_source") != {
                "id": str(self.source_snapshot_id),
                "sha256": self.source_snapshot.sha256,
            }:
                raise ValidationError("Historical excerpt provenance fingerprint mismatch.")
            source = self.source_snapshot.payload
            for key, identity in (("positions", "id"), ("participants", "id")):
                selected_ids = {p[identity] for p in self.payload[key]}
                if self.payload[key] != [p for p in source[key] if p[identity] in selected_ids]:
                    raise ValidationError("Historical selection differs from its immutable source.")
            people = {p["id"] for p in self.payload["participants"]}
            positions = {p["id"] for p in self.payload["positions"]}
            if self.payload["cells"] != [
                c for c in source["cells"] if c["participant_id"] in people and c["position_id"] in positions
            ]:
                raise ValidationError("Historical exact cell selection differs from its immutable source.")


class GenerationRun(ImmutableRecord):
    snapshot = models.OneToOneField(GenerationSnapshot, on_delete=models.PROTECT, related_name="run")
    job = models.OneToOneField("jobs.Job", on_delete=models.PROTECT, related_name="generation_run")

    def clean(self):
        if self.job.kind != "GENERATE" or self.job.payload != {
            "snapshot_id": str(self.snapshot_id),
            "sha256": self.snapshot.sha256,
        }:
            raise ValidationError("Generation run must bind its exact authorized job.")


class SnapshotContentInput(ImmutableRecord):
    snapshot = models.ForeignKey(GenerationSnapshot, on_delete=models.PROTECT, related_name="content_inputs")
    ordinal = models.PositiveIntegerField()
    confirmation = models.ForeignKey("archive.ContentConfirmation", on_delete=models.PROTECT)
    payload = models.JSONField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["snapshot", "ordinal"], name="exports_unique_content_ordinal")]

    def clean(self):
        from apps.exports.content_inputs import SCHEMA, load_content

        entries = self.snapshot.payload.get("content_editions", [])
        if (
            self.snapshot.kind != "ARCHIVE_NOTES"
            or self.snapshot.payload.get("schema") != 2
            or self.ordinal >= len(entries)
            or entries[self.ordinal] != self.payload
            or self.payload.get("schema") != SCHEMA
            or self.payload.get("confirmation_id") != str(self.confirmation_id)
            or self.payload.get("revision_id") != str(self.confirmation.inspection.revision_id)
            or self.payload.get("fingerprint") != self.confirmation.inspection.fingerprint
        ):
            raise ValidationError("Content pin must match its exact versioned authorization payload.")
        load_content(self.payload, using=self._state.db or "default", verify=False)


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
    position = models.ForeignKey("projects.ProjectPosition", on_delete=models.PROTECT, null=True, blank=True)
    participant = models.ForeignKey("projects.ProjectParticipant", on_delete=models.PROTECT, null=True, blank=True)
    ordinal = models.PositiveIntegerField(default=0)
    part = models.ForeignKey("catalog.Part", on_delete=models.PROTECT)
    assignment = models.ForeignKey("archive.ArchiveAssignment", on_delete=models.PROTECT)
    archive_file = models.ForeignKey("archive.ArchiveFile", on_delete=models.PROTECT)
    source_version = models.ForeignKey("archive.SourceVersion", on_delete=models.PROTECT)
    sha256 = models.CharField(max_length=64)
    byte_size = models.PositiveBigIntegerField()
    file_revision = models.PositiveBigIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["snapshot", "position", "participant"], name="exports_unique_cell_pin"),
            models.UniqueConstraint(
                fields=["snapshot", "ordinal"],
                condition=models.Q(position__isnull=True, participant__isnull=True),
                name="exports_unique_archive_ordinal",
            ),
        ]

    def clean(self):
        if self.snapshot.kind != "ARCHIVE_NOTES" and (
            self.position.project_id != self.snapshot.project_id
            or self.participant.project_id != self.snapshot.project_id
        ):
            raise ValidationError("Pinned cell belongs to another project.")
        if self.snapshot.kind == "ARCHIVE_NOTES" and (self.participant_id or self.position_id or self.ordinal < 1):
            raise ValidationError("Archive pins require ordered documents without project identities.")
        if (
            self.assignment.archive_file_id != self.archive_file_id
            or self.assignment.part_id != self.part_id
            or self.archive_file.source_version_id != self.source_version_id
            or self.archive_file.sha256 != self.sha256
            or self.archive_file.byte_size != self.byte_size
        ):
            raise ValidationError("Pinned input identity does not match its source.")


class ExportArtifact(ImmutableRecord):
    variant = models.CharField(max_length=8, choices=[("READING", "READING"), ("PRINT", "PRINT")], default="READING")
    run = models.ForeignKey(GenerationRun, on_delete=models.PROTECT, related_name="artifacts")
    participant = models.ForeignKey("projects.ProjectParticipant", on_delete=models.PROTECT, null=True, blank=True)
    relative_path = models.CharField(max_length=512, unique=True)
    sha256 = models.CharField(max_length=64)
    byte_size = models.PositiveBigIntegerField()
    manifest = models.JSONField()
    intent = models.OneToOneField("jobs.OperationIntent", on_delete=models.PROTECT)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["run", "participant"], name="exports_unique_person_artifact"),
            models.UniqueConstraint(
                fields=["run"], condition=models.Q(participant__isnull=True), name="exports_unique_contents_artifact"
            ),
        ]

    def clean(self):
        try:
            publication = ExportPublication.objects.get(pk=self.intent.payload["publication"])
            stage = publication.stages.get(attempt=self.intent.attempt)
        except (KeyError, ValueError, ExportPublication.DoesNotExist, ExportStage.DoesNotExist):
            raise ValidationError("Artifact publication identity is invalid.") from None
        if (
            self.intent.state != "APPLIED"
            or self.intent.job_id != self.run.job_id
            or self.intent.key != "artifact:" + (self.participant_id.hex if self.participant_id else "contents")
            or self.variant != self.run.snapshot.payload.get("output_variant", "READING")
            or publication.run_id != self.run_id
            or publication.participant_id != self.participant_id
            or publication.relative_path != self.relative_path
            or (stage.sha256, stage.byte_size, stage.manifest) != (self.sha256, self.byte_size, self.manifest)
            or self.intent.result != stage.receipt
        ):
            raise ValidationError("Artifact must match its exact applied publication receipt.")


class ExportPublication(ImmutableRecord):
    run = models.ForeignKey(GenerationRun, on_delete=models.PROTECT, related_name="publications")
    participant = models.ForeignKey("projects.ProjectParticipant", on_delete=models.PROTECT, null=True, blank=True)
    relative_path = models.CharField(max_length=512, unique=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["run", "participant"], name="exports_unique_person_publication"),
            models.UniqueConstraint(
                fields=["run"], condition=models.Q(participant__isnull=True), name="exports_unique_contents_publication"
            ),
        ]

    def clean(self):
        from core.paths import relative_path

        if (self.run.snapshot.kind in {"CONTENTS", "ARCHIVE_NOTES"}) != (self.participant_id is None) or (
            self.participant_id
            and not self.run.snapshot.participants.filter(participant_id=self.participant_id).exists()
        ):
            raise ValidationError("Publication participant is not authorized by this snapshot.")
        if relative_path(self.relative_path) != self.relative_path or self.relative_path.startswith(".staging/"):
            raise ValidationError("Invalid publication path.")


class ExportStage(ImmutableRecord):
    publication = models.ForeignKey(ExportPublication, on_delete=models.PROTECT, related_name="stages")
    attempt = models.PositiveIntegerField()
    sha256 = models.CharField(max_length=64)
    byte_size = models.PositiveBigIntegerField()
    manifest = models.JSONField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["publication", "attempt"], name="exports_unique_attempt_stage")]

    def clean(self):
        import re

        if not re.fullmatch(r"[0-9a-f]{64}", self.sha256) or not 0 < self.byte_size <= 104_857_600:
            raise ValidationError("Invalid bounded stage identity.")
        snapshot = self.publication.run.snapshot
        if (
            self.manifest.get("snapshot_id"),
            self.manifest.get("snapshot_sha256"),
            self.manifest.get("participant_id"),
        ) != (
            str(snapshot.pk),
            snapshot.sha256,
            str(self.publication.participant_id) if self.publication.participant_id else None,
        ):
            raise ValidationError("Stage manifest does not identify its exact snapshot and participant.")
        if snapshot.payload.get("output_variant") == "PRINT":
            plan = self.manifest.get("print_plan", {})
            if (
                not isinstance(plan, dict)
                or not plan.get("sheets")
                or len(plan["sheets"]) != self.manifest.get("page_count")
            ):
                raise ValidationError("Print stage must contain a complete physical sheet manifest.")

    @property
    def relative_path(self):
        return f".staging/{self.publication_id.hex}/attempt-{self.attempt}.pdf"

    @property
    def receipt(self):
        return {"stage": str(self.pk), "sha256": self.sha256, "size": self.byte_size}


class ExportCompletion(ImmutableRecord):
    run = models.OneToOneField(GenerationRun, on_delete=models.PROTECT, related_name="completion")
    inventory = models.JSONField()
    sha256 = models.CharField(max_length=64)

    def clean(self):
        from apps.exports.generation import inventory
        from apps.projects.preflight_services import fingerprint

        if self.inventory != inventory(self.run) or self.sha256 != fingerprint(self.inventory):
            raise ValidationError("Completion must identify the complete verified artifact inventory.")
