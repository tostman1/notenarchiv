"""Recovery and publication require the still-held singleton OS process lock."""

import json
import re
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

from django.db import connections, transaction
from django.db.models import F
from django.db.models.functions import Now
from django.utils import timezone

from apps.jobs.models import AttemptRecord, Job, OperationIntent, WorkerLease
from apps.jobs.services import queue


class Cancelled(RuntimeError):
    pass


class Interrupted(RuntimeError):
    pass


class RetryableFailure(RuntimeError):
    """Only explicit transient failures may retry an idempotent handler."""


class ReviewRequired(RuntimeError):
    """A known effect needs an explicit domain decision before further use."""


class NoEffect(ValueError):
    """Only an apply callback may assert that no external mutation occurred."""


def metadata(context, apply):
    """Run short pure DB metadata under the same current publisher fence."""
    context._authority.assert_owned()
    using, attempt = context._monitor.using, context._attempt
    with transaction.atomic(using=using):
        queue._touch_lease(attempt.lease, using)
        context._authority.assert_owned()
        context.check_cancelled()
        result = apply()
        queue._touch_lease(attempt.lease, using)
        return result


def _acknowledge(handler, context, intent):
    # Metadata only: this runs after the exact receipt is APPLIED, in the same
    # fenced transaction, including successor recovery of a cancelled attempt.
    if handler and handler.acknowledge:
        handler.acknowledge(context, intent)


def bounded_data(value):
    if not isinstance(value, dict):
        raise ValueError("Operation data must be an object")
    encoded = json.dumps(value, allow_nan=False)
    if len(encoded.encode("utf-8")) > queue.PAYLOAD_MAX_BYTES:
        raise ValueError("Operation data exceeds its limit")
    return json.loads(encoded)


def acquire_owned(authority, *, using="default"):
    authority.assert_owned()
    database = str(connections[using].settings_dict["NAME"])
    if (
        database != ":memory:"
        and not database.startswith("file:")
        and authority.path.resolve() != Path(database).resolve().parent / "worker.lock"
    ):
        raise RuntimeError("Worker ownership must use the database's canonical lock")
    # An unexpired DB lease is not proof of a live process. The OS lock is.
    owner = uuid4()
    with transaction.atomic(using=using):
        WorkerLease.objects.using(using).filter(pk=1).update(
            owner=owner,
            generation=F("generation") + 1,
            expires_at=Now() + timedelta(seconds=queue.LEASE_SECONDS),
            heartbeat_at=Now(),
        )
        row = WorkerLease.objects.using(using).get(pk=1)
    return queue.Lease(owner, row.generation)


def check_cancelled(attempt, *, using="default"):
    if (
        not WorkerLease.objects.using(using)
        .filter(pk=1, owner=attempt.lease.owner, generation=attempt.lease.generation, expires_at__gt=Now())
        .exists()
    ):
        raise queue.StaleAttempt("Worker lease is no longer valid")
    job = queue._attempt_rows(attempt, using).first()
    if job is None:
        raise queue.StaleAttempt("Attempt is no longer valid")
    if job.cancel_requested:
        raise Cancelled("Cancellation requested")


def request_cancel(job_id, *, using="default"):
    with transaction.atomic(using=using):
        jobs = Job.objects.using(using).filter(pk=job_id)
        if jobs.filter(status=Job.Status.QUEUED).update(
            cancel_requested=True, status=Job.Status.CANCELLED, finished_at=Now(), error_code="CANCELLED"
        ):
            return True
        return bool(jobs.filter(status=Job.Status.RUNNING).update(cancel_requested=True))


def publish(context, key, payload, apply):
    """Persist intent, then fence the short final no-clobber callback.

    Domain code stages/validates outside this boundary. A crash/exception after
    external mutation leaves PENDING, requiring the registered reconciler.
    This is not an atomic DB/filesystem transaction or an exactly-once promise.
    """
    context._authority.assert_owned()
    if not re.fullmatch(r"[a-zA-Z0-9_.:-]{1,80}", key):
        raise ValueError("Invalid operation key")
    payload = bounded_data(payload)
    using, attempt = context._monitor.using, context._attempt
    handler = queue.HANDLERS.get(attempt.kind)
    with transaction.atomic(using=using):
        queue._touch_lease(attempt.lease, using)
        check_cancelled(attempt, using=using)
        intent, created = OperationIntent.objects.using(using).get_or_create(
            job_id=attempt.job_id,
            key=key,
            defaults={"attempt": attempt.number, "payload": payload},
        )
        if intent.payload != payload:
            raise ValueError("Operation key cannot change meaning")
        if intent.state == OperationIntent.State.APPLIED:
            _acknowledge(handler, context, intent)
            return intent.result
        if not created and intent.state != OperationIntent.State.ABANDONED:
            raise Interrupted("An unresolved operation requires reconciliation")
        intent.state, intent.attempt = OperationIntent.State.PENDING, attempt.number
        intent.save(using=using, update_fields=["state", "attempt"])
    no_effect = False
    try:
        with transaction.atomic(using=using):
            queue._touch_lease(attempt.lease, using)
            context._authority.assert_owned()
            check_cancelled(attempt, using=using)
            try:
                result = bounded_data(apply())
            except NoEffect:
                no_effect = True
                raise
            queue._touch_lease(attempt.lease, using)
            intent.state, intent.result = OperationIntent.State.APPLIED, result
            intent.save(using=using, update_fields=["state", "result"])
            _acknowledge(handler, context, intent)
            queue._touch_lease(attempt.lease, using)
            return result
    except NoEffect:
        if no_effect:
            with transaction.atomic(using=using):
                queue._touch_lease(attempt.lease, using)
                context._authority.assert_owned()
                if not queue._attempt_rows(attempt, using).exists():
                    raise queue.StaleAttempt("Attempt is no longer active") from None
                changed = (
                    OperationIntent.objects.using(using)
                    .filter(pk=intent.pk, attempt=attempt.number, state="PENDING")
                    .update(state="ABANDONED")
                )
                if changed != 1:
                    raise queue.StaleAttempt("Operation is no longer pending") from None
        raise


def _retry_allowed(job, handler):
    return bool(handler and handler.idempotent and job.kind != Job.Kind.PRINT and job.attempt < handler.max_attempts)


def complete(attempt, *, status, error_code, retry=False, using="default"):
    with transaction.atomic(using=using):
        queue._touch_lease(attempt.lease, using)
        job = queue._attempt_rows(attempt, using).first()
        if job is None:
            raise queue.StaleAttempt("Attempt is no longer valid")
        uncertain = job.operations.using(using).filter(state__in=["PENDING", "REVIEW_REQUIRED"]).exists()
        can_retry = (
            retry and _retry_allowed(job, queue.HANDLERS.get(job.kind)) and not job.cancel_requested and not uncertain
        )
        if retry and not can_retry and status == Job.Status.FAILED:
            error_code = "RETRY_EXHAUSTED"
        terminal = queue.finish(attempt, status=status, error_code=error_code, using=using)
        if can_retry:
            Job.objects.using(using).filter(pk=job.pk, attempt=attempt.number).update(
                status=Job.Status.QUEUED,
                progress=0,
                finished_at=None,
                lease_owner=None,
                lease_expires_at=None,
                available_at=Now() + timedelta(seconds=min(60, 2 ** (attempt.number - 1))),
            )
            return Job.Status.QUEUED
        return terminal


class RecoveryContext:
    def __init__(self, job, monitor, authority):
        self.job_id, self.payload = job.pk, job.payload
        self.monitor, self.authority = monitor, authority
        self.using, self.attempt_number = monitor.using, job.attempt

    def checkpoint(self):
        self.authority.assert_owned()
        self.monitor.ensure_alive()
        queue.heartbeat(self.monitor.lease, using=self.monitor.using)


def recover_interrupted(monitor, authority):
    """Reconcile only after acquiring the dead predecessor's OS lock.

    Hooks inspect the durable intent and report APPLIED/ABANDONED/REVIEW_REQUIRED;
    they must not blindly repeat external effects. Domain publication belongs to
    its own package. Unresolved effects and every interrupted PRINT require review.
    """
    using, lease = monitor.using, monitor.lease
    authority.assert_owned()
    for job in Job.objects.using(using).filter(status=Job.Status.RUNNING):
        handler = queue.HANDLERS.get(job.kind)
        context = RecoveryContext(job, monitor, authority)
        try:
            queue.validate_payload(job.kind, job.payload, job.payload_version)
        except queue.InvalidPayload:
            handler = None
        for intent in job.operations.using(using).filter(state="PENDING"):
            context.checkpoint()
            try:
                if not handler or not handler.reconcile:
                    raise ValueError("No reconciler installed")
                state, result = handler.reconcile(context, intent)
                if state not in {"APPLIED", "ABANDONED", "REVIEW_REQUIRED"}:
                    raise ValueError("Invalid reconciliation outcome")
                result = bounded_data(result)
            except queue.StaleAttempt:
                raise
            except Exception:
                state, result = "REVIEW_REQUIRED", {}
            with transaction.atomic(using=using):
                queue._touch_lease(lease, using)
                authority.assert_owned()
                intent.state, intent.result = state, result
                intent.save(using=using, update_fields=["state", "result"])
                if state == "APPLIED":
                    _acknowledge(handler, context, intent)
        cleanup_failed = False
        if handler and handler.recover_cleanup:
            try:
                handler.recover_cleanup(context)
            except queue.StaleAttempt:
                raise
            except Exception:
                # Unverified cleanup must not authorize another heavy attempt.
                cleanup_failed = True
        with transaction.atomic(using=using):
            queue._touch_lease(lease, using)
            job.refresh_from_db(using=using)
            uncertain = job.operations.using(using).filter(state__in=["PENDING", "REVIEW_REQUIRED"]).exists()
            status, error = Job.Status.FAILED, "RECOVERY_UNSAFE"
            if job.kind == Job.Kind.PRINT:
                status, error = Job.Status.REVIEW_REQUIRED, "PRINT_ACCEPTANCE_UNKNOWN"
            elif uncertain or cleanup_failed:
                status, error = Job.Status.REVIEW_REQUIRED, "OPERATION_UNCERTAIN"
            elif job.cancel_requested:
                status, error = Job.Status.CANCELLED, "CANCELLED"
            elif _retry_allowed(job, handler):
                status, error = Job.Status.QUEUED, "INTERRUPTED"
            record, _created = AttemptRecord.objects.using(using).get_or_create(
                job=job,
                number=job.attempt,
                defaults={"started_at": job.started_at or job.created_at, "status": "RUNNING"},
            )
            record.status = Job.Status.FAILED if status == Job.Status.QUEUED else status
            record.error_code, record.finished_at = error, timezone.now()
            record.save(using=using)
            job.status, job.error_code = status, error
            job.lease_owner, job.lease_expires_at = None, None
            job.finished_at = None if status == Job.Status.QUEUED else timezone.now()
            job.available_at = timezone.now() + timedelta(seconds=min(60, 2 ** (max(1, job.attempt) - 1)))
            if status == Job.Status.QUEUED:
                job.progress = 0
            job.save(using=using)
