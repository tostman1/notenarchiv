"""Single-process worker runner with independent idle/busy heartbeats."""

import logging
import threading
import time

from django.db import connections

from apps.jobs.models import Job
from apps.jobs.services import lifecycle, queue
from core.locking import ProcessLock
from core.processes import ProcessCleanupError, run_process

log = logging.getLogger(__name__)


class WorkerUnavailable(RuntimeError):
    """A duplicate worker or unfinished attempt requires operator attention."""


class Heartbeats:
    def __init__(self, lease, using, shutdown=None, authority=None):
        self.lease, self.using = lease, using
        self.attempt = None
        self.shutdown = shutdown or threading.Event()
        self.authority = authority
        self.guard = threading.Lock()
        self.stop = threading.Event()
        self.lost = threading.Event()
        self.thread = threading.Thread(target=self._run, name="worker-heartbeat", daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exception):
        self.stop.set()
        self.thread.join(timeout=10)
        if self.thread.is_alive():
            raise WorkerUnavailable("Worker heartbeat did not stop")

    def _run(self):
        try:
            while not self.stop.wait(queue.HEARTBEAT_SECONDS):
                try:
                    with self.guard:
                        queue.heartbeat(self.lease, self.attempt, using=self.using)
                except Exception:
                    self.lost.set()
                    log.error("Worker heartbeat failed", exc_info=True)
                    return
        finally:
            connections.close_all()  # Django connections belong to this heartbeat thread.

    def ensure_alive(self):
        if self.lost.is_set():
            raise queue.StaleAttempt("Worker heartbeat was lost")

    def begin(self, attempt):
        with self.guard:
            self.ensure_alive()
            self.attempt = attempt

    def checkpoint(self, attempt, progress=None):
        with self.guard:
            self.ensure_alive()
            if self.attempt != attempt:
                raise queue.StaleAttempt("Attempt is no longer active")
            queue.heartbeat(self.lease, attempt, progress=progress, using=self.using)

    def finish(self, attempt, **outcome):
        with self.guard:
            self.ensure_alive()
            status = lifecycle.complete(attempt, using=self.using, **outcome)
            self.attempt = None
            return status


class JobContext:
    def __init__(self, attempt, monitor, payload):
        self.job_id = attempt.job_id
        self.payload = payload
        self._attempt, self._monitor = attempt, monitor
        self._authority = monitor.authority

    def checkpoint(self, progress=None):
        self._monitor.checkpoint(self._attempt, progress)
        self.check_cancelled()

    def check_cancelled(self):
        self._monitor.ensure_alive()
        lifecycle.check_cancelled(self._attempt, using=self._monitor.using)
        if self._monitor.shutdown.is_set():
            raise lifecycle.Interrupted("Worker is stopping")

    def publish(self, key, payload, apply):
        self.check_cancelled()
        return lifecycle.publish(self, key, payload, apply)

    def run_process(self, arguments, *, timeout):
        return run_process(arguments, timeout=timeout, checkpoint=self.check_cancelled)


def execute(attempt, monitor):
    monitor.begin(attempt)
    started = time.monotonic()
    log.info("Job started", extra={"event": "job_started", "job_id": attempt.job_id})
    status, error, retry = Job.Status.SUCCEEDED, "", False
    if attempt.kind not in queue.HANDLERS:
        status, error = Job.Status.FAILED, "HANDLER_UNAVAILABLE"
    else:
        try:
            payload = queue.validate_payload(attempt.kind, attempt.payload, attempt.payload_version)
        except queue.InvalidPayload:
            status, error = Job.Status.FAILED, "PAYLOAD_INVALID"
        else:
            try:
                context = JobContext(attempt, monitor, payload)
                context.check_cancelled()
                queue.HANDLERS[attempt.kind].run(context)
                context.check_cancelled()
            except queue.StaleAttempt:
                raise
            except ProcessCleanupError:
                monitor.finish(attempt, status=Job.Status.REVIEW_REQUIRED, error_code="PROCESS_CLEANUP_UNCERTAIN")
                raise WorkerUnavailable("Process termination was not verified") from None
            except lifecycle.Cancelled:
                status, error = Job.Status.CANCELLED, "CANCELLED"
                if attempt.kind == Job.Kind.PRINT:
                    status, error = Job.Status.REVIEW_REQUIRED, "PRINT_ACCEPTANCE_UNKNOWN"
            except (lifecycle.Interrupted, lifecycle.RetryableFailure):
                status, error, retry = Job.Status.FAILED, "INTERRUPTED", True
                if attempt.kind == Job.Kind.PRINT:
                    status, error, retry = Job.Status.REVIEW_REQUIRED, "PRINT_ACCEPTANCE_UNKNOWN", False
            except Exception:
                status, error = Job.Status.FAILED, "HANDLER_FAILED"
                if attempt.kind == Job.Kind.PRINT:
                    status, error = Job.Status.REVIEW_REQUIRED, "PRINT_ACCEPTANCE_UNKNOWN"
    status = monitor.finish(attempt, status=status, error_code=error, retry=retry)
    log.info(
        "Job finished",
        extra={
            "event": "job_finished" if status == Job.Status.SUCCEEDED else "job_failed",
            "job_id": attempt.job_id,
            "duration_ms": int((time.monotonic() - started) * 1000),
        },
    )


def run_worker(lock_path, *, once=False, poll_seconds=1, shutdown=None, using="default"):
    """Hold the OS lock for the full worker lifetime, even after lease expiry.

    Recovery requires this canonical OS lock, not a lease-expiry assumption.
    """
    shutdown = shutdown or threading.Event()
    try:
        lock = ProcessLock(lock_path)
        lock.__enter__()
    except OSError:
        raise WorkerUnavailable("Worker process lock is unavailable") from None
    try:
        lease = lifecycle.acquire_owned(lock, using=using)
        try:
            with Heartbeats(lease, using, shutdown, lock) as monitor:
                lifecycle.recover_interrupted(monitor, lock)
                log.info("Worker started", extra={"event": "service_started"})
                while not shutdown.is_set():
                    monitor.ensure_alive()
                    attempt = queue.claim_next(lease, using=using)
                    if attempt is not None:
                        execute(attempt, monitor)
                    if once:
                        break
                    if attempt is None:
                        shutdown.wait(poll_seconds)
        finally:
            queue.release_worker(lease, using=using)
    finally:
        lock.__exit__()
