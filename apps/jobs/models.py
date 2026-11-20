"""Durable queue metadata and the global single-heavy-job lease (WP-05a)."""

import uuid

from django.db import models
from django.db.models import Q
from django.utils import timezone


class Job(models.Model):
    class Kind(models.TextChoices):
        INDEX_SCAN = "INDEX_SCAN"
        OCR = "OCR"
        INTEGRITY_CHECK = "INTEGRITY_CHECK"
        ARCHIVE_PUBLISH = "ARCHIVE_PUBLISH"
        GENERATE = "GENERATE"
        SCAN_PROCESS = "SCAN_PROCESS"
        PRINT = "PRINT"

    class Status(models.TextChoices):
        QUEUED = "QUEUED"
        RUNNING = "RUNNING"
        SUCCEEDED = "SUCCEEDED"
        FAILED = "FAILED"
        CANCELLED = "CANCELLED"
        REVIEW_REQUIRED = "REVIEW_REQUIRED"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    kind = models.CharField(max_length=24, choices=Kind)
    payload_version = models.PositiveSmallIntegerField(default=1)
    payload = models.JSONField(default=dict)
    status = models.CharField(max_length=24, choices=Status, default=Status.QUEUED, db_index=True)
    progress = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True)
    finished_at = models.DateTimeField(null=True)
    cancel_requested = models.BooleanField(default=False)
    error_code = models.CharField(max_length=32, blank=True)
    attempt = models.PositiveBigIntegerField(default=0)
    lease_owner = models.UUIDField(null=True)
    lease_expires_at = models.DateTimeField(null=True)
    available_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["created_at", "id"]
        constraints = [
            models.UniqueConstraint(fields=["status"], condition=Q(status="RUNNING"), name="jobs_one_running"),
            models.CheckConstraint(condition=Q(progress__lte=100), name="jobs_progress_percent"),
            models.CheckConstraint(
                condition=~Q(status="RUNNING") | (Q(lease_owner__isnull=False) & Q(lease_expires_at__isnull=False)),
                name="jobs_running_has_lease",
            ),
            models.CheckConstraint(
                condition=Q(status__in=["QUEUED", "RUNNING", "SUCCEEDED", "FAILED", "CANCELLED", "REVIEW_REQUIRED"]),
                name="jobs_valid_status",
            ),
        ]


class AttemptRecord(models.Model):
    job = models.ForeignKey(Job, on_delete=models.PROTECT, related_name="history")
    number = models.PositiveBigIntegerField()
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True)
    status = models.CharField(max_length=24, choices=Job.Status)
    error_code = models.CharField(max_length=32, blank=True)

    class Meta:
        ordering = ["number"]
        constraints = [models.UniqueConstraint(fields=["job", "number"], name="jobs_unique_attempt")]


class OperationIntent(models.Model):
    class State(models.TextChoices):
        PENDING = "PENDING"
        APPLIED = "APPLIED"
        ABANDONED = "ABANDONED"
        REVIEW_REQUIRED = "REVIEW_REQUIRED"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(Job, on_delete=models.PROTECT, related_name="operations")
    key = models.CharField(max_length=80)
    attempt = models.PositiveBigIntegerField()
    payload = models.JSONField(default=dict)
    result = models.JSONField(default=dict)
    state = models.CharField(max_length=24, choices=State, default=State.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["job", "key"], name="jobs_unique_operation"),
            models.CheckConstraint(
                condition=Q(state__in=["PENDING", "APPLIED", "ABANDONED", "REVIEW_REQUIRED"]),
                name="jobs_valid_operation_state",
            ),
        ]


class WorkerLease(models.Model):
    """The migration creates row 1; no per-job heartbeat doubles as health."""

    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    owner = models.UUIDField(null=True)
    generation = models.PositiveBigIntegerField(default=0)
    expires_at = models.DateTimeField(null=True)
    heartbeat_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(id=1), name="jobs_single_worker_lease"),
            models.CheckConstraint(
                condition=(Q(owner__isnull=True) & Q(expires_at__isnull=True))
                | (Q(owner__isnull=False) & Q(expires_at__isnull=False)),
                name="jobs_worker_lease_consistent",
            ),
        ]
