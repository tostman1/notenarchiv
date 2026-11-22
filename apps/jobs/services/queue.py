"""Short SQLite write transactions, conditional claims and fenced updates."""

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID, uuid4

from django.db import transaction
from django.db.models import Exists, F, Q
from django.db.models.functions import Now

from apps.jobs.models import AttemptRecord, Job, OperationIntent, WorkerLease

LEASE_SECONDS = 30
HEARTBEAT_SECONDS = 5
PAYLOAD_MAX_BYTES = 16 * 1024


class InvalidPayload(ValueError):
    """Payloads require a registered, versioned domain validator."""


class StaleAttempt(RuntimeError):
    """The worker or attempt lost its lease; no result may be committed."""


@dataclass(frozen=True)
class Handler:
    validate: Callable[[dict], dict]
    run: Callable
    idempotent: bool = False
    max_attempts: int = 1
    reconcile: Callable | None = None
    acknowledge: Callable | None = None

    def __post_init__(self):
        if type(self.idempotent) is not bool or type(self.max_attempts) is not int or not 1 <= self.max_attempts <= 5:
            raise ValueError("Invalid bounded retry policy")
        if self.max_attempts > 1 and not self.idempotent:
            raise ValueError("Retries require an explicitly idempotent handler")


# Domain packages install real handlers as they are implemented. No demo jobs.
HANDLERS = {}


def validate_payload(kind, payload, version=1):
    try:
        if kind not in Job.Kind.values or kind not in HANDLERS or version != 1 or type(version) is not int:
            raise ValueError
        if not isinstance(payload, dict):
            raise ValueError
        encoded = json.dumps(payload, allow_nan=False)
        if len(encoded.encode("utf-8")) > PAYLOAD_MAX_BYTES:
            raise ValueError
        normalized = HANDLERS[kind].validate(json.loads(encoded))
        if not isinstance(normalized, dict):
            raise ValueError
        encoded = json.dumps(normalized, allow_nan=False)
        if len(encoded.encode("utf-8")) > PAYLOAD_MAX_BYTES:
            raise ValueError
        return json.loads(encoded)
    except (ValueError, TypeError, RecursionError, KeyError) as exc:
        raise InvalidPayload("Unsupported job or invalid payload") from exc


def enqueue(kind, payload, *, version=1, using="default"):
    normalized = validate_payload(kind, payload, version)
    # Claims compare with SQLite's statement clock (millisecond precision).
    # Python microseconds can be ahead in the same clock tick, particularly on
    # Windows. Immediate enqueue uses the same DB timebase as claim/retry fencing.
    job = Job.objects.using(using).create(kind=kind, payload=normalized, payload_version=version, available_at=Now())
    job.refresh_from_db(using=using, fields=["available_at"])
    return job


@dataclass(frozen=True)
class Lease:
    owner: UUID
    generation: int


@dataclass(frozen=True)
class Attempt:
    job_id: UUID
    lease: Lease
    number: int
    kind: str
    payload: dict
    payload_version: int


def acquire_worker(*, owner=None, using="default"):
    owner = owner or uuid4()
    with transaction.atomic(using=using):
        changed = (
            WorkerLease.objects.using(using)
            .filter(pk=1)
            .filter(Q(owner__isnull=True) | Q(expires_at__lte=Now()))
            .filter(~Exists(Job.objects.using(using).filter(status=Job.Status.RUNNING)))
            .update(
                owner=owner,
                generation=F("generation") + 1,
                expires_at=Now() + timedelta(seconds=LEASE_SECONDS),
                heartbeat_at=Now(),
            )
        )
        if not changed:
            return None
        row = WorkerLease.objects.using(using).get(pk=1)
        return Lease(owner, row.generation)


def _touch_lease(lease, using):
    changed = (
        WorkerLease.objects.using(using)
        .filter(
            pk=1,
            owner=lease.owner,
            generation=lease.generation,
            expires_at__gt=Now(),
        )
        .update(heartbeat_at=Now(), expires_at=Now() + timedelta(seconds=LEASE_SECONDS))
    )
    if changed != 1:
        raise StaleAttempt("Worker lease is no longer valid")


def claim_next(lease, *, using="default"):
    with transaction.atomic(using=using):
        # Write first: select_for_update does not provide row locking on SQLite.
        _touch_lease(lease, using)
        jobs = Job.objects.using(using)
        if jobs.filter(status=Job.Status.RUNNING).exists():
            return None
        job = jobs.filter(status=Job.Status.QUEUED, cancel_requested=False, available_at__lte=Now()).first()
        if job is None:
            return None
        changed = jobs.filter(pk=job.pk, status=Job.Status.QUEUED).update(
            status=Job.Status.RUNNING,
            attempt=F("attempt") + 1,
            lease_owner=lease.owner,
            lease_expires_at=Now() + timedelta(seconds=LEASE_SECONDS),
            started_at=Now(),
        )
        if changed != 1:
            return None
        AttemptRecord.objects.using(using).create(
            job=job, number=job.attempt + 1, started_at=jobs.get(pk=job.pk).started_at, status=Job.Status.RUNNING
        )
        return Attempt(job.id, lease, job.attempt + 1, job.kind, job.payload, job.payload_version)


def _attempt_rows(attempt, using):
    return Job.objects.using(using).filter(
        pk=attempt.job_id,
        status=Job.Status.RUNNING,
        attempt=attempt.number,
        lease_owner=attempt.lease.owner,
        lease_expires_at__gt=Now(),
    )


def heartbeat(lease, attempt=None, *, progress=None, using="default"):
    if progress is not None and (type(progress) is not int or not 0 <= progress <= 100 or attempt is None):
        raise ValueError("Progress must be an integer percentage for an active attempt")
    if attempt is not None and attempt.lease != lease:
        raise StaleAttempt("Attempt belongs to another worker")
    with transaction.atomic(using=using):
        _touch_lease(lease, using)
        if attempt is not None:
            rows = _attempt_rows(attempt, using)
            changes = {"lease_expires_at": Now() + timedelta(seconds=LEASE_SECONDS)}
            if progress is not None:
                rows = rows.filter(progress__lte=progress)
                changes["progress"] = progress
            if rows.update(**changes) != 1:
                raise StaleAttempt("Attempt is no longer valid or progress regressed")


def finish(attempt, *, status=Job.Status.SUCCEEDED, error_code="", using="default"):
    allowed_errors = {
        "HANDLER_FAILED",
        "PAYLOAD_INVALID",
        "HANDLER_UNAVAILABLE",
        "PRINT_ACCEPTANCE_UNKNOWN",
        "INTERRUPTED",
        "RETRY_EXHAUSTED",
        "OPERATION_UNCERTAIN",
        "CANCELLED",
        "RECOVERY_UNSAFE",
        "PROCESS_CLEANUP_UNCERTAIN",
    }
    if status not in {Job.Status.SUCCEEDED, Job.Status.FAILED, Job.Status.REVIEW_REQUIRED, Job.Status.CANCELLED}:
        raise ValueError("Unsupported completion transition")
    if (status == Job.Status.SUCCEEDED and error_code) or (
        status != Job.Status.SUCCEEDED and error_code not in allowed_errors
    ):
        raise ValueError("Invalid completion error code")
    with transaction.atomic(using=using):
        _touch_lease(attempt.lease, using)
        row = _attempt_rows(attempt, using).first()
        if row is None:
            raise StaleAttempt("Attempt is no longer valid")
        if (
            OperationIntent.objects.using(using)
            .filter(job_id=row.pk, state__in=["PENDING", "REVIEW_REQUIRED"])
            .exists()
        ):
            status, error_code = Job.Status.REVIEW_REQUIRED, "OPERATION_UNCERTAIN"
        elif row.cancel_requested and status != Job.Status.REVIEW_REQUIRED:
            if row.kind == Job.Kind.PRINT:
                status, error_code = Job.Status.REVIEW_REQUIRED, "PRINT_ACCEPTANCE_UNKNOWN"
            else:
                status, error_code = Job.Status.CANCELLED, "CANCELLED"
        changes = {"status": status, "finished_at": Now(), "lease_expires_at": None, "error_code": error_code}
        if status == Job.Status.SUCCEEDED:
            changes["progress"] = 100
        if _attempt_rows(attempt, using).update(**changes) != 1:
            raise StaleAttempt("Attempt is no longer valid")
        record, _created = AttemptRecord.objects.using(using).get_or_create(
            job_id=row.pk,
            number=attempt.number,
            defaults={"started_at": row.started_at, "status": Job.Status.RUNNING},
        )
        record.status, record.error_code = status, error_code
        record.finished_at = Now()
        record.save(using=using, update_fields=["status", "error_code", "finished_at"])
        return status


def release_worker(lease, *, using="default"):
    return (
        WorkerLease.objects.using(using)
        .filter(
            pk=1,
            owner=lease.owner,
            generation=lease.generation,
            expires_at__gt=Now(),
        )
        .filter(~Exists(Job.objects.using(using).filter(status=Job.Status.RUNNING)))
        .update(owner=None, expires_at=None)
        == 1
    )


def worker_is_healthy(*, using="default"):
    return (
        WorkerLease.objects.using(using)
        .filter(
            pk=1,
            owner__isnull=False,
            expires_at__gt=Now(),
            heartbeat_at__gte=Now() - timedelta(seconds=2 * HEARTBEAT_SECONDS),
            heartbeat_at__lte=Now(),
        )
        .exists()
    )
