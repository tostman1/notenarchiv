"""Recovery, durable intent reconciliation, bounded retries and cancellation."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.jobs.models import Job, OperationIntent, WorkerLease
from apps.jobs.services import lifecycle, queue, worker
from core.locking import ProcessLock
from tests.test_queue import queue_db as _queue_fixture
from tests.test_queue import validate_synthetic

queue_db = _queue_fixture


def ready(job):
    Job.objects.filter(pk=job.pk).update(available_at=timezone.now() - timedelta(seconds=1))


def test_receipt_and_domain_ack_rollback_together_then_recover_even_when_cancelled(queue_db, monkeypatch, tmp_path):
    from apps.archive.models import SourceFolder

    effect = tmp_path / "synthetic-ack-effect"
    acknowledgements = []

    def acknowledge(ctx, intent):
        assert intent.state == "APPLIED" and intent.result == {"verified": True}
        SourceFolder.objects.using(ctx.using).get_or_create(relative_path="SyntheticAcknowledgement")
        acknowledgements.append(1)
        if len(acknowledgements) == 1:
            raise SystemExit("Synthetic crash inside metadata acknowledgement")

    def reconcile(ctx, intent):
        ctx.checkpoint()
        return "APPLIED", {"verified": effect.read_text() == "Synthetic effect"}

    monkeypatch.setitem(
        queue.HANDLERS,
        Job.Kind.INTEGRITY_CHECK,
        queue.Handler(validate_synthetic, lambda ctx: None, True, 2, reconcile, acknowledge),
    )
    job = queue.enqueue(Job.Kind.INTEGRITY_CHECK, {"value": 1})
    with ProcessLock(tmp_path / "worker.lock") as authority:
        lease = lifecycle.acquire_owned(authority)
        attempt = queue.claim_next(lease)
        monitor = worker.Heartbeats(lease, "default", authority=authority)
        monitor.begin(attempt)
        context = worker.JobContext(attempt, monitor, {"value": 1})

        def apply():
            effect.write_text("Synthetic effect")
            return {"verified": True}

        with pytest.raises(SystemExit):
            context.publish("ack-result", {}, apply)
    assert job.operations.get().state == "PENDING" and not SourceFolder.objects.exists()
    assert lifecycle.request_cancel(job.pk)
    worker.run_worker(tmp_path / "worker.lock", once=True)
    job.refresh_from_db()
    assert job.status == "CANCELLED" and job.operations.get().state == "APPLIED"
    assert SourceFolder.objects.get().relative_path == "SyntheticAcknowledgement"
    assert acknowledgements == [1, 1]
    with pytest.raises((RuntimeError, queue.StaleAttempt)):
        context.commit_metadata(lambda: pytest.fail("Dead predecessor must not commit metadata"))


def test_metadata_fence_blocks_cancelled_and_expired_attempts(queue_db, tmp_path):
    with ProcessLock(tmp_path / "worker.lock") as authority:
        lease = lifecycle.acquire_owned(authority)
        job = queue.enqueue(Job.Kind.INTEGRITY_CHECK, {"value": 1})
        attempt = queue.claim_next(lease)
        monitor = worker.Heartbeats(lease, "default", authority=authority)
        monitor.begin(attempt)
        context = worker.JobContext(attempt, monitor, {"value": 1})
        assert context.commit_metadata(lambda: "short metadata result") == "short metadata result"
        lifecycle.request_cancel(job.pk)
        with pytest.raises(lifecycle.Cancelled):
            context.commit_metadata(lambda: pytest.fail("Cancelled attempt must not commit"))
        WorkerLease.objects.filter(pk=1).update(expires_at=timezone.now() - timedelta(seconds=1))
        with pytest.raises(queue.StaleAttempt):
            context.commit_metadata(lambda: pytest.fail("Expired attempt must not commit"))


@pytest.mark.parametrize("inside_ack", [False, True])
def test_only_apply_can_assert_no_effect_ack_failure_remains_uncertain(queue_db, monkeypatch, tmp_path, inside_ack):
    effect = tmp_path / "synthetic-known-effect"

    def apply():
        if not inside_ack:
            raise lifecycle.NoEffect("Synthetic pre-effect refusal")
        effect.write_text("Synthetic known effect")
        return {"verified": True}

    def acknowledge(ctx, intent):
        raise lifecycle.NoEffect("A metadata failure cannot erase an external effect")

    def run(ctx):
        ctx.publish("known-effect", {}, apply)

    monkeypatch.setitem(
        queue.HANDLERS, Job.Kind.INTEGRITY_CHECK, queue.Handler(validate_synthetic, run, acknowledge=acknowledge)
    )
    job = queue.enqueue(Job.Kind.INTEGRITY_CHECK, {"value": 1})
    worker.run_worker(tmp_path / "worker.lock", once=True)
    job.refresh_from_db()
    assert job.status == ("REVIEW_REQUIRED" if inside_ack else "FAILED")
    assert job.operations.get().state == ("PENDING" if inside_ack else "ABANDONED")
    assert effect.exists() is inside_ack


def test_queued_cancel_and_running_cancel_wait_for_actual_stop(queue_db):
    queued = queue.enqueue(Job.Kind.INTEGRITY_CHECK, {"value": 1})
    assert lifecycle.request_cancel(queued.pk)
    queued.refresh_from_db()
    assert queued.status == Job.Status.CANCELLED and queued.attempt == 0
    job = queue.enqueue(Job.Kind.INTEGRITY_CHECK, {"value": 1})
    lease = queue.acquire_worker()
    attempt = queue.claim_next(lease)
    assert lifecycle.request_cancel(job.pk)
    job.refresh_from_db()
    assert job.status == Job.Status.RUNNING and job.finished_at is None
    with pytest.raises(lifecycle.Cancelled):
        lifecycle.check_cancelled(attempt)
    queue.finish(attempt)  # Called only after processor and all children have stopped.
    job.refresh_from_db()
    assert job.status == Job.Status.CANCELLED and job.history.get().status == "CANCELLED"
    assert not lifecycle.request_cancel(job.pk)


def test_crash_after_external_effect_reconciles_without_republishing(queue_db, monkeypatch, tmp_path):
    output = tmp_path / "synthetic-effect"
    calls = []

    def apply():
        calls.append(1)
        output.write_text("verified synthetic result")
        return {"verified": True}

    def handler(ctx):
        assert ctx.publish("result:1", {"version": 1}, apply) == {"verified": True}

    def reconcile(ctx, intent):
        ctx.checkpoint()
        assert intent.payload == {"version": 1}
        return "APPLIED", {"verified": output.read_text() == "verified synthetic result"}

    monkeypatch.setitem(
        queue.HANDLERS, Job.Kind.INTEGRITY_CHECK, queue.Handler(validate_synthetic, handler, True, 3, reconcile)
    )
    job = queue.enqueue(Job.Kind.INTEGRITY_CHECK, {"value": 1})
    with ProcessLock(tmp_path / "worker.lock") as authority:
        lease = lifecycle.acquire_owned(authority)
        old = queue.claim_next(lease)
        monitor = worker.Heartbeats(lease, "default", authority=authority)
        monitor.begin(old)
        context = worker.JobContext(old, monitor, {"value": 1})

        def crash():
            apply()
            raise SystemExit("synthetic crash before DB acknowledgement")

        with pytest.raises(SystemExit):
            context.publish("result:1", {"version": 1}, crash)
    assert job.operations.get().state == "PENDING"
    # The old lease is deliberately still fresh: only OS ownership permits takeover.
    assert WorkerLease.objects.get(pk=1).expires_at > timezone.now()
    worker.run_worker(tmp_path / "worker.lock", once=True)
    job.refresh_from_db()
    assert job.status == Job.Status.QUEUED and job.operations.get().state == "APPLIED"
    with pytest.raises(queue.StaleAttempt):
        queue.finish(old)
    with pytest.raises(queue.StaleAttempt):
        context.publish("result:2", {}, apply)
    ready(job)
    worker.run_worker(tmp_path / "worker.lock", once=True)
    job.refresh_from_db()
    assert job.status == Job.Status.SUCCEEDED and calls == [1]
    assert list(job.history.values_list("status", flat=True)) == ["FAILED", "SUCCEEDED"]


@pytest.mark.parametrize(
    "kind,idempotent,pending,expected",
    [
        (Job.Kind.PRINT, True, False, "REVIEW_REQUIRED"),
        (Job.Kind.INTEGRITY_CHECK, False, False, "FAILED"),
        (Job.Kind.INTEGRITY_CHECK, True, True, "REVIEW_REQUIRED"),
    ],
)
def test_restart_never_blindly_replays_unknown_effects(
    queue_db, monkeypatch, tmp_path, kind, idempotent, pending, expected
):
    calls = []
    monkeypatch.setitem(
        queue.HANDLERS,
        kind,
        queue.Handler(validate_synthetic, lambda ctx: calls.append(1), idempotent, 2 if idempotent else 1),
    )
    job = queue.enqueue(kind, {"value": 1})
    old = queue.claim_next(queue.acquire_worker())
    if pending:
        OperationIntent.objects.create(job=job, key="effect", attempt=old.number)
    worker.run_worker(tmp_path / "worker.lock", once=True)
    worker.run_worker(tmp_path / "worker.lock", once=True)
    job.refresh_from_db()
    assert job.status == expected and not calls and job.attempt == 1


def test_retries_are_bounded_and_reuse_applied_intents(queue_db, monkeypatch, tmp_path):
    effects = []

    def run(ctx):
        ctx.publish("once", {}, lambda: effects.append(1) or {"done": True})
        raise lifecycle.RetryableFailure("synthetic private detail")

    monkeypatch.setitem(queue.HANDLERS, Job.Kind.INTEGRITY_CHECK, queue.Handler(validate_synthetic, run, True, 2))
    job = queue.enqueue(Job.Kind.INTEGRITY_CHECK, {"value": 1})
    worker.run_worker(tmp_path / "worker.lock", once=True)
    job.refresh_from_db()
    assert job.status == "QUEUED" and job.available_at > timezone.now()
    worker.run_worker(tmp_path / "worker.lock", once=True)
    job.refresh_from_db()
    assert job.attempt == 1  # Backoff is actually observed by the claimant.
    ready(job)
    worker.run_worker(tmp_path / "worker.lock", once=True)
    worker.run_worker(tmp_path / "worker.lock", once=True)
    job.refresh_from_db()
    assert job.status == "FAILED" and job.error_code == "RETRY_EXHAUSTED" and job.attempt == 2
    assert effects == [1] and job.history.count() == 2


def test_cancel_checkpoint_finishes_only_after_handler_cleanup(queue_db, monkeypatch, tmp_path):
    stopped = []

    def run(ctx):
        try:
            lifecycle.request_cancel(ctx.job_id)
            assert Job.objects.get(pk=ctx.job_id).status == "RUNNING"
            ctx.checkpoint(20)
        finally:
            stopped.append(True)
            assert Job.objects.get(pk=ctx.job_id).finished_at is None

    monkeypatch.setitem(queue.HANDLERS, Job.Kind.INTEGRITY_CHECK, queue.Handler(validate_synthetic, run))
    job = queue.enqueue(Job.Kind.INTEGRITY_CHECK, {"value": 1})
    worker.run_worker(tmp_path / "worker.lock", once=True)
    job.refresh_from_db()
    assert stopped == [True] and job.status == "CANCELLED" and job.finished_at


def test_operation_key_cannot_change_payload_and_unresolved_effect_is_reviewed(queue_db, monkeypatch, tmp_path):
    def run(ctx):
        ctx.publish("effect", {}, lambda: (_ for _ in ()).throw(RuntimeError("synthetic uncertainty")))

    monkeypatch.setitem(queue.HANDLERS, Job.Kind.INTEGRITY_CHECK, queue.Handler(validate_synthetic, run, True, 3))
    job = queue.enqueue(Job.Kind.INTEGRITY_CHECK, {"value": 1})
    worker.run_worker(tmp_path / "worker.lock", once=True)
    job.refresh_from_db()
    assert job.status == "REVIEW_REQUIRED" and job.error_code == "OPERATION_UNCERTAIN"
    assert job.operations.get().state == "PENDING"


@pytest.mark.parametrize("policy", [(False, 2), (True, 0), (True, 6), (True, True)])
def test_invalid_retry_policy_fails_closed(policy):
    with pytest.raises(ValueError):
        queue.Handler(validate_synthetic, lambda ctx: None, *policy)


def test_unverified_process_cleanup_requires_review_and_blocks_retry(queue_db, monkeypatch, tmp_path):
    from core.processes import ProcessCleanupError

    def run(ctx):
        lifecycle.request_cancel(ctx.job_id)
        raise ProcessCleanupError("synthetic stop failure")

    monkeypatch.setitem(queue.HANDLERS, Job.Kind.INTEGRITY_CHECK, queue.Handler(validate_synthetic, run, True, 3))
    job = queue.enqueue(Job.Kind.INTEGRITY_CHECK, {"value": 1})
    with pytest.raises(worker.WorkerUnavailable):
        worker.run_worker(tmp_path / "worker.lock", once=True)
    worker.run_worker(tmp_path / "worker.lock", once=True)
    job.refresh_from_db()
    assert job.status == "REVIEW_REQUIRED" and job.error_code == "PROCESS_CLEANUP_UNCERTAIN" and job.attempt == 1


def test_print_cancel_racing_with_completion_never_claims_successful_cancellation(queue_db, monkeypatch):
    monkeypatch.setitem(queue.HANDLERS, Job.Kind.PRINT, queue.Handler(validate_synthetic, lambda ctx: None))
    job = queue.enqueue(Job.Kind.PRINT, {"value": 1})
    attempt = queue.claim_next(queue.acquire_worker())
    lifecycle.request_cancel(job.pk)
    queue.finish(attempt)
    job.refresh_from_db()
    assert job.status == "REVIEW_REQUIRED" and job.error_code == "PRINT_ACCEPTANCE_UNKNOWN"
