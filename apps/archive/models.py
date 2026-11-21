"""Archive identities, protected history and orthogonal workflow dimensions."""

import math
import uuid
from pathlib import PurePosixPath

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

from apps.archive.validation import bounded_json, page_metadata, path_value, reference, region_metadata
from core.paths import storage_key

HASH = RegexValidator(r"\A[0-9a-f]{64}\Z", "A lowercase SHA-256 is required.")
AUDIT_TARGETS = ("folder", "source_file", "source_version", "archive_file", "file_operation")


def exactly_one_target():
    condition = Q()
    for selected in AUDIT_TARGETS:
        condition |= Q(**{name + "__isnull": name != selected for name in AUDIT_TARGETS})
    return condition


class Record(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if kwargs.get("using"):
            self._state.db = kwargs["using"]
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Archive history is retained; use an explicit state transition.")


class SourceFolder(Record):
    class IndexState(models.TextChoices):
        NEW = "NEW"
        INDEXING = "INDEXING"
        INDEXED = "INDEXED"
        PARTIAL_FAILURE = "PARTIAL_FAILURE"

    relative_path = models.CharField(max_length=1024, unique=True, blank=True)
    revision = models.PositiveBigIntegerField(default=1)
    inventory_fingerprint = models.CharField(max_length=64, blank=True, validators=[HASH])
    index_state = models.CharField(max_length=24, choices=IndexState, default=IndexState.NEW)
    file_count = models.PositiveIntegerField(default=0)
    indexed_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    proposed_arrangements = models.ManyToManyField("catalog.Arrangement", through="FolderArrangementProposal")

    def clean(self):
        path_value(self.relative_path, allow_root=True)
        if (
            not self._state.adding
            and type(self).objects.using(self._state.db or "default").get(pk=self.pk).relative_path
            != self.relative_path
        ):
            raise ValidationError("Source folder identity is immutable.")

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(index_state__in=["NEW", "INDEXING", "INDEXED", "PARTIAL_FAILURE"]),
                name="archive_folder_valid_index",
            ),
            models.CheckConstraint(
                condition=Q(indexed_count__lte=F("file_count") - F("failed_count")),
                name="archive_folder_bounded_counts",
            ),
        ]


class FolderArrangementProposal(Record):
    folder = models.ForeignKey(SourceFolder, on_delete=models.PROTECT, related_name="arrangement_proposals")
    arrangement = models.ForeignKey("catalog.Arrangement", on_delete=models.PROTECT)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["folder", "arrangement"], name="archive_unique_folder_proposal")]


class SourceFile(Record):
    class Presence(models.TextChoices):
        PRESENT = "PRESENT"
        MISSING = "MISSING"
        CHANGED = "CHANGED"

    folder = models.ForeignKey(SourceFolder, on_delete=models.PROTECT, related_name="files")
    relative_path = models.CharField(max_length=1024, unique=True)
    revision = models.PositiveBigIntegerField(default=1)
    observed_size = models.PositiveBigIntegerField(null=True, blank=True)
    observed_mtime_ns = models.BigIntegerField(null=True, blank=True)
    presence = models.CharField(max_length=16, choices=Presence, default=Presence.PRESENT)
    last_seen_at = models.DateTimeField(default=timezone.now)
    current_version = models.ForeignKey(
        "SourceVersion", on_delete=models.PROTECT, null=True, blank=True, related_name="current_sources"
    )

    def clean(self):
        path_value(self.relative_path)
        parent = str(PurePosixPath(self.relative_path).parent)
        parent = "" if parent == "." else parent
        if self.folder_id and reference(self, "folder").relative_path != parent:
            raise ValidationError("The source file must belong to its actual folder.")
        if self.current_version_id and reference(self, "current_version").source_file_id != self.pk:
            raise ValidationError("Current version belongs to another source file.")
        if not self._state.adding:
            previous = type(self).objects.using(self._state.db or "default").get(pk=self.pk)
            if previous.relative_path != self.relative_path or previous.folder_id != self.folder_id:
                raise ValidationError("Source file identity is immutable.")

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(presence__in=["PRESENT", "MISSING", "CHANGED"]), name="archive_source_valid_presence"
            )
        ]


class SourceVersion(Record):
    class PdfState(models.TextChoices):
        UNCHECKED = "UNCHECKED"
        VALID = "VALID"
        INVALID = "INVALID"
        LIMIT_EXCEEDED = "LIMIT_EXCEEDED"

    source_file = models.ForeignKey(SourceFile, on_delete=models.PROTECT, related_name="versions")
    sha256 = models.CharField(max_length=64, validators=[HASH], db_index=True)
    byte_size = models.PositiveBigIntegerField()
    source_mtime_ns = models.BigIntegerField(null=True, blank=True)
    revision = models.PositiveBigIntegerField(default=1)
    pdf_state = models.CharField(max_length=24, choices=PdfState, default=PdfState.UNCHECKED)
    page_info = models.JSONField(default=list, blank=True, validators=[page_metadata])

    def clean(self):
        page_metadata(self.page_info)
        if self.pdf_state == self.PdfState.VALID and (not self.page_info or not 0 < self.byte_size <= 104_857_600):
            raise ValidationError("Validated PDFs require bounded bytes and page metadata.")
        if not self._state.adding:
            previous = type(self).objects.using(self._state.db or "default").get(pk=self.pk)
            if any(
                getattr(previous, field) != getattr(self, field)
                for field in ("source_file_id", "sha256", "byte_size", "source_mtime_ns")
            ):
                raise ValidationError("Source content identity is immutable.")
            if previous.pdf_state != self.PdfState.UNCHECKED and (
                previous.pdf_state != self.pdf_state or previous.page_info != self.page_info
            ):
                raise ValidationError("Recorded PDF validation is immutable.")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["source_file", "sha256"], name="archive_unique_source_hash"),
            models.CheckConstraint(
                condition=Q(pdf_state__in=["UNCHECKED", "VALID", "INVALID", "LIMIT_EXCEEDED"]),
                name="archive_version_valid_pdf_state",
            ),
        ]


class RootKind(models.TextChoices):
    CLEAN = "CLEAN"
    PROCESSED = "PROCESSED"


class UsableFiles(models.QuerySet):
    def usable(self):
        return self.filter(
            review_state="CONFIRMED",
            publication_state="AVAILABLE",
            arrangement__active=True,
            publication_operation__state="APPLIED",
            publication_operation__intent__state="APPLIED",
            approved_proposal__state="APPROVED",
            source_version__pdf_state="VALID",
        )


class ArchiveFile(Record):
    class Kind(models.TextChoices):
        BASE = "BASE"
        DERIVATIVE = "DERIVATIVE"

    class PublicationState(models.TextChoices):
        UNPUBLISHED = "UNPUBLISHED"
        AVAILABLE = "AVAILABLE"
        MISSING = "MISSING"
        CORRUPT = "CORRUPT"

    class ReviewState(models.TextChoices):
        PENDING = "PENDING"
        APPROVAL_REQUESTED = "APPROVAL_REQUESTED"
        CONFIRMED = "CONFIRMED"
        REJECTED = "REJECTED"
        WITHDRAWN = "WITHDRAWN"

    class CandidateState(models.TextChoices):
        UNASSESSED = "UNASSESSED"
        PROPOSED = "PROPOSED"
        CONFLICT = "CONFLICT"
        UNKNOWN = "UNKNOWN"

    source_version = models.ForeignKey(SourceVersion, on_delete=models.PROTECT, related_name="archive_files")
    arrangement = models.ForeignKey(
        "catalog.Arrangement", on_delete=models.PROTECT, null=True, blank=True, related_name="archive_files"
    )
    revision = models.PositiveBigIntegerField(default=1)
    root_kind = models.CharField(max_length=16, choices=RootKind, default=RootKind.CLEAN)
    relative_path = models.CharField(max_length=512)
    path_key = models.CharField(max_length=4096, editable=False)
    sha256 = models.CharField(max_length=64, validators=[HASH], db_index=True)
    byte_size = models.PositiveBigIntegerField()
    kind = models.CharField(max_length=16, choices=Kind, default=Kind.BASE)
    derived_from = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="derivatives"
    )
    processing_profile = models.CharField(max_length=80, blank=True)
    processing_version = models.CharField(max_length=80, blank=True)
    publication_state = models.CharField(max_length=16, choices=PublicationState, default=PublicationState.UNPUBLISHED)
    review_state = models.CharField(max_length=24, choices=ReviewState, default=ReviewState.PENDING)
    candidate_state = models.CharField(max_length=16, choices=CandidateState, default=CandidateState.UNASSESSED)
    current_proposal = models.ForeignKey(
        "ArchiveProposal", on_delete=models.PROTECT, null=True, blank=True, related_name="current_for"
    )
    approved_proposal = models.ForeignKey(
        "ArchiveProposal", on_delete=models.PROTECT, null=True, blank=True, related_name="approved_for"
    )
    publication_operation = models.ForeignKey(
        "FileOperation", on_delete=models.PROTECT, null=True, blank=True, related_name="published_files"
    )
    confirmed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    objects = UsableFiles.as_manager()

    def full_clean(self, *args, **kwargs):
        self.path_key = storage_key(path_value(self.relative_path))
        return super().full_clean(*args, **kwargs)

    def save(self, *args, **kwargs):
        if kwargs.get("update_fields") is not None:
            kwargs["update_fields"] = set(kwargs["update_fields"]) | {"path_key"}
        return super().save(*args, **kwargs)

    def clean(self):
        if self.source_version_id and self.kind == self.Kind.BASE:
            version = reference(self, "source_version")
            if self.sha256 != version.sha256 or self.byte_size != version.byte_size:
                raise ValidationError("Base files must be byte-identical to their source version.")
            if self._state.adding and version.pdf_state != SourceVersion.PdfState.VALID:
                raise ValidationError("Base files require a structurally validated PDF.")
        if self.kind == self.Kind.DERIVATIVE and (
            not self.processing_profile.strip() or not self.processing_version.strip()
        ):
            raise ValidationError("Derivatives require an explicit processing profile and version.")
        if self.derived_from_id:
            parent = reference(self, "derived_from")
            if parent.source_version_id != self.source_version_id or parent.pk == self.pk:
                raise ValidationError("Invalid derivative provenance.")
            seen = {self.pk}
            while parent:
                if parent.pk in seen or len(seen) > 32:
                    raise ValidationError("Cyclic or excessive derivative provenance.")
                seen.add(parent.pk)
                parent = reference(parent, "derived_from")
        for proposal in (reference(self, "current_proposal"), reference(self, "approved_proposal")):
            if proposal is not None and proposal.archive_file_id != self.pk:
                raise ValidationError("Proposal belongs to another archive file.")
        if self.publication_state == self.PublicationState.AVAILABLE or self.review_state == self.ReviewState.CONFIRMED:
            operation = reference(self, "publication_operation")
            if operation is None or operation.archive_file_id != self.pk or operation.state != "APPLIED":
                raise ValidationError("Availability requires an applied publication operation.")
            if (
                operation.target_root != self.root_kind
                or operation.target_path != self.relative_path
                or operation.expected_sha256 != self.sha256
                or operation.expected_size != self.byte_size
            ):
                raise ValidationError("Publication receipt does not identify these bytes and path.")
        if self.review_state == self.ReviewState.CONFIRMED:
            proposal = reference(self, "approved_proposal")
            if (
                proposal is None
                or proposal.state != "APPROVED"
                or proposal.arrangement_id != self.arrangement_id
                or self.arrangement_id is None
                or self.confirmed_by_id is None
                or self.confirmed_at is None
                or proposal.approved_by_id != self.confirmed_by_id
                or proposal.approved_at != self.confirmed_at
                or self.publication_operation_id is None
                or not self.operations.filter(
                    proposal_id=self.approved_proposal_id, kind="CANONICALIZE", state="APPLIED"
                ).exists()
            ):
                raise ValidationError("Confirmation requires inspected assignments and verified publication.")
            expected_parts = set(proposal.parts.values_list("part_id", flat=True))
            confirmed_parts = set(self.assignments.filter(state="CONFIRMED").values_list("part_id", flat=True))
            if not expected_parts or confirmed_parts != expected_parts:
                raise ValidationError("Confirmed assignments must match the approved proposal.")
        if not self._state.adding:
            previous = type(self).objects.using(self._state.db or "default").get(pk=self.pk)
            if (
                self.review_state == "CONFIRMED"
                and previous.review_state != "CONFIRMED"
                and self.publication_state != "AVAILABLE"
            ):
                raise ValidationError("New confirmation requires an available verified copy.")
            immutable = (
                "source_version_id",
                "sha256",
                "byte_size",
                "kind",
                "root_kind",
                "derived_from_id",
                "processing_profile",
                "processing_version",
            )
            if any(getattr(previous, field) != getattr(self, field) for field in immutable):
                raise ValidationError("Archive content identity is immutable; create a separate version/derivative.")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["root_kind", "path_key"], name="archive_unique_storage_path"),
            models.UniqueConstraint(
                fields=["source_version"], condition=Q(kind="BASE"), name="archive_one_base_per_version"
            ),
            models.CheckConstraint(
                condition=Q(publication_state__in=["UNPUBLISHED", "AVAILABLE", "MISSING", "CORRUPT"]),
                name="archive_valid_publication_state",
            ),
            models.CheckConstraint(
                condition=Q(review_state__in=["PENDING", "APPROVAL_REQUESTED", "CONFIRMED", "REJECTED", "WITHDRAWN"]),
                name="archive_valid_review_state",
            ),
            models.CheckConstraint(
                condition=Q(candidate_state__in=["UNASSESSED", "PROPOSED", "CONFLICT", "UNKNOWN"]),
                name="archive_valid_candidate_state",
            ),
            models.CheckConstraint(
                condition=(
                    Q(kind="BASE", root_kind="CLEAN", derived_from__isnull=True)
                    | Q(kind="DERIVATIVE", root_kind="PROCESSED", derived_from__isnull=False)
                ),
                name="archive_kind_root_provenance",
            ),
            models.CheckConstraint(condition=Q(byte_size__gt=0), name="archive_nonempty_file"),
            models.CheckConstraint(
                condition=(
                    ~Q(review_state="CONFIRMED")
                    | Q(
                        arrangement__isnull=False,
                        approved_proposal__isnull=False,
                        confirmed_by__isnull=False,
                        confirmed_at__isnull=False,
                        publication_operation__isnull=False,
                    )
                ),
                name="archive_confirmation_evidence",
            ),
            models.CheckConstraint(
                condition=~Q(publication_state="AVAILABLE") | Q(publication_operation__isnull=False),
                name="archive_availability_receipt",
            ),
        ]


class ArchiveProposal(Record):
    class State(models.TextChoices):
        DRAFT = "DRAFT"
        APPROVAL_REQUESTED = "APPROVAL_REQUESTED"
        APPROVED = "APPROVED"
        REJECTED = "REJECTED"

    archive_file = models.ForeignKey(ArchiveFile, on_delete=models.PROTECT, related_name="proposals")
    revision = models.PositiveBigIntegerField()
    arrangement = models.ForeignKey("catalog.Arrangement", on_delete=models.PROTECT, null=True, blank=True)
    sealed = models.BooleanField(default=False)
    state = models.CharField(max_length=24, choices=State, default=State.DRAFT)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="archive_proposals")
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="archive_approval_requests",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="archive_approvals"
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    def clean(self):
        if not self._state.adding:
            previous = type(self).objects.using(self._state.db or "default").get(pk=self.pk)
            if any(
                getattr(previous, field) != getattr(self, field)
                for field in ("archive_file_id", "revision", "arrangement_id", "created_by_id")
            ) or (previous.sealed and not self.sealed):
                raise ValidationError("Proposal snapshots are immutable; create a new revision.")
            if previous.state in {"APPROVED", "REJECTED"} and any(
                getattr(previous, field) != getattr(self, field)
                for field in ("state", "requested_by_id", "approved_by_id", "approved_at")
            ):
                raise ValidationError("Final proposal decisions are retained as immutable history.")
            transitions = {
                "DRAFT": {"DRAFT", "APPROVAL_REQUESTED", "REJECTED"},
                "APPROVAL_REQUESTED": {"APPROVAL_REQUESTED", "APPROVED", "REJECTED"},
                "APPROVED": {"APPROVED"},
                "REJECTED": {"REJECTED"},
            }
            if self.state not in transitions.get(previous.state, set()):
                raise ValidationError("Invalid proposal decision transition.")
        if self.state in {"APPROVAL_REQUESTED", "APPROVED"} and (not self.sealed or self.requested_by_id is None):
            raise ValidationError("Approval requests require a sealed proposal and reviewer.")
        if self.state == self.State.APPROVED and (
            not self.sealed
            or self.approved_by_id is None
            or self.approved_by_id != self.requested_by_id
            or self.approved_at is None
            or self.arrangement_id is None
            or not self.inspections.filter(
                reviewer_id=self.approved_by_id, inspected_sha256=reference(self, "archive_file").sha256
            ).exists()
        ):
            raise ValidationError("Approval requires this reviewer's exact version/proposal inspection.")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["archive_file", "revision"], name="archive_unique_proposal_revision"),
            models.CheckConstraint(condition=Q(revision__gt=0), name="archive_positive_proposal_revision"),
            models.CheckConstraint(
                condition=Q(state__in=["DRAFT", "APPROVAL_REQUESTED", "APPROVED", "REJECTED"]),
                name="archive_proposal_valid_state",
            ),
            models.CheckConstraint(
                condition=~Q(state="APPROVED")
                | Q(sealed=True, approved_by__isnull=False, approved_at__isnull=False, arrangement__isnull=False),
                name="archive_approved_proposal_evidence",
            ),
        ]


class ProposalPart(Record):
    proposal = models.ForeignKey(ArchiveProposal, on_delete=models.PROTECT, related_name="parts")
    part = models.ForeignKey("catalog.Part", on_delete=models.PROTECT, related_name="archive_proposals")

    def clean(self):
        if self.proposal_id and (
            reference(self, "proposal").sealed or reference(self, "proposal").state != ArchiveProposal.State.DRAFT
        ):
            raise ValidationError("Sealed proposal parts cannot change.")
        if not self._state.adding:
            raise ValidationError("Proposal snapshots are immutable.")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["proposal", "part"], name="archive_unique_proposed_part")]


class UsableAssignments(models.QuerySet):
    def usable(self):
        return self.filter(
            state="CONFIRMED",
            accepted_proposal_id=F("archive_file__approved_proposal_id"),
            archive_file__in=ArchiveFile.objects.using(self.db).usable(),
            part__active=True,
            part__instrument__active=True,
        )


class ArchiveAssignment(Record):
    class State(models.TextChoices):
        CONFIRMED = "CONFIRMED"
        WITHDRAWN = "WITHDRAWN"

    archive_file = models.ForeignKey(ArchiveFile, on_delete=models.PROTECT, related_name="assignments")
    part = models.ForeignKey("catalog.Part", on_delete=models.PROTECT, related_name="archive_assignments")
    accepted_proposal = models.ForeignKey(
        ArchiveProposal, on_delete=models.PROTECT, related_name="accepted_assignments"
    )
    state = models.CharField(max_length=16, choices=State, default=State.CONFIRMED)
    objects = UsableAssignments.as_manager()

    def clean(self):
        if self.accepted_proposal_id:
            proposal = reference(self, "accepted_proposal")
            if proposal.archive_file_id != self.archive_file_id or proposal.state != "APPROVED":
                raise ValidationError("Assignment requires an approved proposal for the same file.")
            if not proposal.parts.filter(part_id=self.part_id).exists():
                raise ValidationError("Assignment part was not approved in that proposal.")
        if not self._state.adding:
            previous = type(self).objects.using(self._state.db or "default").get(pk=self.pk)
            if previous.archive_file_id != self.archive_file_id or previous.part_id != self.part_id:
                raise ValidationError("Assignment identity is protected.")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["archive_file", "part"], name="archive_unique_assignment"),
            models.CheckConstraint(
                condition=Q(state__in=["CONFIRMED", "WITHDRAWN"]), name="archive_assignment_valid_state"
            ),
        ]


class ReviewInspection(Record):
    proposal = models.ForeignKey(ArchiveProposal, on_delete=models.PROTECT, related_name="inspections")
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="archive_inspections")
    inspected_sha256 = models.CharField(max_length=64, validators=[HASH])
    explicit_attestation = models.BooleanField(default=False)

    def clean(self):
        if self.proposal_id and (
            not reference(self, "proposal").sealed
            or self.inspected_sha256 != reference(self, "proposal").archive_file.sha256
        ):
            raise ValidationError("Inspection must bind the sealed proposal and exact file hash.")
        if self.proposal_id:
            file = reference(reference(self, "proposal"), "archive_file")
            operation = reference(file, "publication_operation")
            if (
                file.publication_state != "AVAILABLE"
                or operation is None
                or operation.state != "APPLIED"
                or reference(operation, "intent") is None
                or operation.intent.state != "APPLIED"
            ):
                raise ValidationError("Inspection requires an available durably published copy.")
        if not self._state.adding:
            raise ValidationError("Inspection evidence is immutable.")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["proposal", "reviewer"], name="archive_unique_reviewer_inspection"),
            models.CheckConstraint(condition=Q(explicit_attestation=True), name="archive_inspection_explicit"),
        ]


class FileOperation(Record):
    class Kind(models.TextChoices):
        COPY = "COPY"
        CANONICALIZE = "CANONICALIZE"
        DERIVATIVE = "DERIVATIVE"

    class State(models.TextChoices):
        PLANNED = "PLANNED"
        STAGED = "STAGED"
        APPLIED = "APPLIED"
        FAILED = "FAILED"
        REVIEW_REQUIRED = "REVIEW_REQUIRED"
        ABANDONED = "ABANDONED"

    archive_file = models.ForeignKey(ArchiveFile, on_delete=models.PROTECT, related_name="operations")
    job = models.ForeignKey("jobs.Job", on_delete=models.PROTECT, related_name="file_operations")
    attempt_record = models.ForeignKey(
        "jobs.AttemptRecord", on_delete=models.PROTECT, null=True, blank=True, related_name="file_operations"
    )
    intent = models.OneToOneField(
        "jobs.OperationIntent", on_delete=models.PROTECT, null=True, blank=True, related_name="file_operation"
    )
    proposal = models.ForeignKey(
        ArchiveProposal, on_delete=models.PROTECT, null=True, blank=True, related_name="operations"
    )
    attempt = models.PositiveBigIntegerField(default=0)
    kind = models.CharField(max_length=16, choices=Kind, default=Kind.COPY)
    state = models.CharField(max_length=24, choices=State, default=State.PLANNED)
    target_root = models.CharField(max_length=16, choices=RootKind, default=RootKind.CLEAN)
    target_path = models.CharField(max_length=512)
    target_key = models.CharField(max_length=4096, editable=False)
    staged_path = models.CharField(max_length=512, blank=True)
    expected_sha256 = models.CharField(max_length=64, validators=[HASH])
    expected_size = models.PositiveBigIntegerField()

    @property
    def effect_key(self):
        return "archive-publish:" + str(self.pk)

    @property
    def expected_receipt(self):
        return {
            "root": self.target_root,
            "path": self.target_path,
            "sha256": self.expected_sha256,
            "size": self.expected_size,
        }

    @property
    def effect_payload(self):
        return {"operation_id": str(self.pk), **self.expected_receipt}

    def full_clean(self, *args, **kwargs):
        self.target_key = storage_key(path_value(self.target_path))
        return super().full_clean(*args, **kwargs)

    def save(self, *args, **kwargs):
        if kwargs.get("update_fields") is not None:
            kwargs["update_fields"] = set(kwargs["update_fields"]) | {"target_key"}
        return super().save(*args, **kwargs)

    def clean(self):
        if self.staged_path:
            path_value(self.staged_path)
        if self.archive_file_id:
            file = reference(self, "archive_file")
            if (
                self.expected_sha256 != file.sha256
                or self.expected_size != file.byte_size
                or self.target_root != file.root_kind
            ):
                raise ValidationError("Publication must identify the exact archive content.")
            if (self.kind == self.Kind.COPY and file.kind != ArchiveFile.Kind.BASE) or (
                self.kind == self.Kind.DERIVATIVE and file.kind != ArchiveFile.Kind.DERIVATIVE
            ):
                raise ValidationError("Operation kind does not match its archive content.")
        if self.staged_path and PurePosixPath(self.staged_path).parts[0] != ".staging":
            raise ValidationError("Staged files must remain in the separate staging directory.")
        if self.state == self.State.STAGED and not self.staged_path:
            raise ValidationError("A staged operation requires its staged path.")
        if self.job_id and reference(self, "job").kind not in {"INDEX_SCAN", "ARCHIVE_PUBLISH", "SCAN_PROCESS"}:
            raise ValidationError("Unsupported archive publication job type.")
        if self.state in {self.State.STAGED, self.State.APPLIED}:
            attempt_record = reference(self, "attempt_record")
            if (
                attempt_record is None
                or attempt_record.job_id != self.job_id
                or attempt_record.number != self.attempt
                or self.attempt < 1
            ):
                raise ValidationError("Publication requires the exact protected attempt record.")
        if self.kind == self.Kind.CANONICALIZE:
            proposal = reference(self, "proposal")
            if proposal is None or proposal.archive_file_id != self.archive_file_id:
                raise ValidationError("Canonical publication requires the same file's proposal.")
        if self.state == self.State.APPLIED:
            intent = reference(self, "intent")
            expected = self.expected_receipt
            if intent is None or intent.state != "APPLIED" or intent.job_id != self.job_id or intent.result != expected:
                raise ValidationError("Applied publication requires the matching durable receipt.")
            if intent.key != self.effect_key or intent.payload != self.effect_payload:
                raise ValidationError("Publication receipt belongs to another logical effect.")
            if intent.attempt != self.attempt:
                raise ValidationError("Receipt belongs to another publication attempt.")
        if not self._state.adding:
            previous = type(self).objects.using(self._state.db or "default").get(pk=self.pk)
            fields = (
                "archive_file_id",
                "job_id",
                "kind",
                "target_root",
                "target_path",
                "expected_sha256",
                "expected_size",
                "proposal_id",
            )
            if any(getattr(previous, field) != getattr(self, field) for field in fields):
                raise ValidationError("Publication intent cannot change meaning.")
            if previous.state == "APPLIED" and any(
                getattr(previous, field) != getattr(self, field)
                for field in ("state", "intent_id", "attempt", "attempt_record_id", "staged_path")
            ):
                raise ValidationError("Applied publication history is immutable.")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["target_root", "target_key"], name="archive_reserved_operation_path"),
            models.CheckConstraint(condition=Q(expected_size__gt=0), name="archive_operation_nonempty"),
            models.CheckConstraint(
                condition=~Q(kind="CANONICALIZE") | Q(proposal__isnull=False), name="archive_canonical_proposal"
            ),
            models.CheckConstraint(
                condition=Q(state__in=["PLANNED", "STAGED", "APPLIED", "FAILED", "REVIEW_REQUIRED", "ABANDONED"]),
                name="archive_operation_valid_state",
            ),
            models.CheckConstraint(
                condition=~Q(state="APPLIED") | Q(intent__isnull=False), name="archive_applied_has_intent"
            ),
            models.CheckConstraint(
                condition=~Q(state__in=["STAGED", "APPLIED"]) | Q(attempt_record__isnull=False, attempt__gt=0),
                name="archive_publication_has_attempt",
            ),
        ]


class RecognitionCandidate(Record):
    class Method(models.TextChoices):
        FILENAME = "FILENAME"
        TEXT_LAYER = "TEXT_LAYER"
        OCR = "OCR"
        MANUAL = "MANUAL"

    source_version = models.ForeignKey(SourceVersion, on_delete=models.PROTECT, related_name="candidates")
    archive_file = models.ForeignKey(
        ArchiveFile, on_delete=models.PROTECT, null=True, blank=True, related_name="candidates"
    )
    input_sha256 = models.CharField(max_length=64, validators=[HASH])
    method = models.CharField(max_length=16, choices=Method)
    excerpt = models.TextField(max_length=4096, blank=True)
    region = models.JSONField(default=dict, blank=True, validators=[region_metadata])
    proposed_work = models.ForeignKey("catalog.Work", on_delete=models.PROTECT, null=True, blank=True)
    proposed_arrangement = models.ForeignKey("catalog.Arrangement", on_delete=models.PROTECT, null=True, blank=True)
    confidence = models.FloatField(null=True, blank=True)
    rule_version = models.CharField(max_length=80)
    reasons = models.JSONField(default=list, blank=True)
    sealed = models.BooleanField(default=False)

    def clean(self):
        region_metadata(self.region)
        bounded_json(self.reasons, maximum=4096)
        if not isinstance(self.reasons, list) or any(
            not isinstance(reason, str) or len(reason) > 80 for reason in self.reasons
        ):
            raise ValidationError("Conflict reasons must be bounded labels.")
        if self.confidence is not None and (not math.isfinite(self.confidence) or not 0 <= self.confidence <= 1):
            raise ValidationError("Confidence must be finite and between zero and one.")
        if self.archive_file_id:
            file = reference(self, "archive_file")
            if file.source_version_id != self.source_version_id or file.sha256 != self.input_sha256:
                raise ValidationError("Evidence must identify the exact archive version.")
        elif self.source_version_id and reference(self, "source_version").sha256 != self.input_sha256:
            raise ValidationError("Evidence must identify the exact source version.")
        if (
            self.proposed_work_id
            and self.proposed_arrangement_id
            and reference(self, "proposed_arrangement").work_id != self.proposed_work_id
        ):
            raise ValidationError("Candidate work/arrangement references disagree.")
        if not self._state.adding:
            previous = type(self).objects.using(self._state.db or "default").get(pk=self.pk)
            for field in self._meta.concrete_fields:
                if field.name not in {"sealed", "created_at"} and getattr(previous, field.attname) != getattr(
                    self, field.attname
                ):
                    raise ValidationError("Recognition evidence is immutable; record a new candidate.")
            if previous.sealed and not self.sealed:
                raise ValidationError("Sealed recognition evidence cannot reopen.")

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(confidence__isnull=True) | Q(confidence__gte=0, confidence__lte=1),
                name="archive_candidate_bounded_confidence",
            ),
            models.CheckConstraint(
                condition=Q(method__in=["FILENAME", "TEXT_LAYER", "OCR", "MANUAL"]),
                name="archive_candidate_valid_method",
            ),
        ]


class CandidatePart(Record):
    candidate = models.ForeignKey(RecognitionCandidate, on_delete=models.PROTECT, related_name="parts")
    part = models.ForeignKey("catalog.Part", on_delete=models.PROTECT)

    def clean(self):
        if not self._state.adding or (self.candidate_id and reference(self, "candidate").sealed):
            raise ValidationError("Sealed recognition parts are immutable.")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["candidate", "part"], name="archive_unique_candidate_part")]


class AuditEvent(Record):
    class Event(models.TextChoices):
        SOURCE_OBSERVED = "SOURCE_OBSERVED"
        SOURCE_MISSING = "SOURCE_MISSING"
        VALIDATED = "VALIDATED"
        PROPOSAL_CREATED = "PROPOSAL_CREATED"
        INSPECTED = "INSPECTED"
        APPROVAL_REQUESTED = "APPROVAL_REQUESTED"
        CONFIRMED = "CONFIRMED"
        REJECTED = "REJECTED"
        WITHDRAWN = "WITHDRAWN"
        COPY_PLANNED = "COPY_PLANNED"
        COPY_APPLIED = "COPY_APPLIED"

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="archive_audit_events"
    )
    event = models.CharField(max_length=32, choices=Event)
    folder = models.ForeignKey(SourceFolder, on_delete=models.PROTECT, null=True, blank=True)
    source_file = models.ForeignKey(SourceFile, on_delete=models.PROTECT, null=True, blank=True)
    source_version = models.ForeignKey(SourceVersion, on_delete=models.PROTECT, null=True, blank=True)
    archive_file = models.ForeignKey(ArchiveFile, on_delete=models.PROTECT, null=True, blank=True)
    file_operation = models.ForeignKey(FileOperation, on_delete=models.PROTECT, null=True, blank=True)
    before = models.JSONField(default=dict, blank=True, validators=[bounded_json])
    after = models.JSONField(default=dict, blank=True, validators=[bounded_json])

    def clean(self):
        if not isinstance(self.before, dict) or not isinstance(self.after, dict):
            raise ValidationError("Audit metadata must be bounded dictionaries.")
        bounded_json(self.before)
        bounded_json(self.after)
        if not self._state.adding:
            raise ValidationError("Audit evidence is append-only.")

    class Meta:
        ordering = ["created_at", "id"]
        constraints = [models.CheckConstraint(condition=exactly_one_target(), name="archive_audit_one_target")]
