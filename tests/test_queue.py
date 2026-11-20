"""Durable model, payload, lease, fencing and worker contract acceptance."""

import subprocess
import sys
from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.jobs.models import Job, WorkerLease
from apps.jobs.services import queue, worker
from core.locking import ProcessLock


def validate_synthetic(payload):
    if set(payload) != {"value"} or type(payload["value"]) is not int or not 0 <= payload["value"] <= 3:
        raise ValueError("synthetic private detail")
    return payload


@pytest.fixture()
def queue_db(db, monkeypatch):
    WorkerLease.objects.get_or_create(pk=1)
    monkeypatch.setattr(
        queue, "HANDLERS", {Job.Kind.INTEGRITY_CHECK: queue.Handler(validate_synthetic, lambda ctx: None)}
    )


def test_enqueue_validate_claim_and_fenced_progress(queue_db):
    payload = {"value": 1}
    job = queue.enqueue(Job.Kind.INTEGRITY_CHECK, payload)
    payload["value"] = 3
    assert Job.objects.get(pk=job.pk).payload == {"value": 1}
    lease = queue.acquire_worker()
    assert queue.acquire_worker() is None
    assert queue.worker_is_healthy()
    attempt = queue.claim_next(lease)
    assert attempt.job_id == job.pk and attempt.number == 1
    queue.enqueue(Job.Kind.INTEGRITY_CHECK, {"value": 2})
    assert queue.claim_next(lease) is None
    queue.heartbeat(lease, attempt, progress=40)
    with pytest.raises(queue.StaleAttempt):
        queue.heartbeat(lease, attempt, progress=39)
    with pytest.raises(queue.StaleAttempt):
        queue.finish(replace(attempt, number=0))
    with pytest.raises(queue.StaleAttempt):
        queue.finish(replace(attempt, lease=replace(lease, owner=uuid4())))
    job.refresh_from_db()
    assert job.status == Job.Status.RUNNING and job.progress == 40
    assert not queue.release_worker(lease)
    queue.finish(attempt)
    with pytest.raises(queue.StaleAttempt):
        queue.finish(attempt)
    job.refresh_from_db()
    assert job.status == Job.Status.SUCCEEDED and job.progress == 100
    assert job.finished_at and job.lease_expires_at is None
    assert queue.release_worker(lease)
    assert not queue.worker_is_healthy()
    successor = queue.acquire_worker()
    assert successor.generation > lease.generation
    with pytest.raises(queue.StaleAttempt):
        queue.claim_next(lease)


@pytest.mark.parametrize(
    "kind,payload,version",
    [
        ("UNKNOWN", {"value": 1}, 1),
        (Job.Kind.PRINT, {"value": 1}, 1),
        (Job.Kind.INTEGRITY_CHECK, {"value": True}, 1),
        (Job.Kind.INTEGRITY_CHECK, [], 1),
        (Job.Kind.INTEGRITY_CHECK, {"value": 1, "secret": "synthetic"}, 1),
        (Job.Kind.INTEGRITY_CHECK, {"value": 1}, 2),
        (Job.Kind.INTEGRITY_CHECK, {"value": 1}, True),
        (Job.Kind.INTEGRITY_CHECK, {"value": "x" * queue.PAYLOAD_MAX_BYTES}, 1),
        (Job.Kind.INTEGRITY_CHECK, {"value": float("nan")}, 1),
    ],
)
def test_reject_invalid_unavailable_and_unbounded_payloads(queue_db, kind, payload, version):
    with pytest.raises(queue.InvalidPayload, match="Unsupported job or invalid payload"):
        queue.enqueue(kind, payload, version=version)
    assert not Job.objects.exists()


def test_expired_attempt_cannot_commit_and_is_not_automatically_reclaimed(queue_db):
    job = queue.enqueue(Job.Kind.INTEGRITY_CHECK, {"value": 1})
    lease = queue.acquire_worker()
    attempt = queue.claim_next(lease)
    expired = timezone.now() - timedelta(seconds=1)
    WorkerLease.objects.filter(pk=1).update(expires_at=expired)
    Job.objects.filter(pk=job.pk).update(lease_expires_at=expired)
    assert not queue.worker_is_healthy()
    for action in (lambda: queue.heartbeat(lease, attempt), lambda: queue.finish(attempt)):
        with pytest.raises(queue.StaleAttempt):
            action()
    assert queue.acquire_worker() is None
    job.refresh_from_db()
    assert job.status == Job.Status.RUNNING and job.attempt == 1
    assert not queue.release_worker(lease)


def test_idle_health_is_freshness_based_and_healthcheck_fails_closed(queue_db):
    with pytest.raises(CommandError, match="unavailable or stale"):
        call_command("worker_healthcheck")
    lease = queue.acquire_worker()
    call_command("worker_healthcheck")
    WorkerLease.objects.filter(pk=1).update(
        heartbeat_at=timezone.now() - timedelta(seconds=queue.HEARTBEAT_SECONDS * 2 + 1)
    )
    assert not queue.worker_is_healthy()
    queue.heartbeat(lease)
    assert queue.worker_is_healthy()
    call_command("worker_healthcheck")


def test_database_enforces_single_heavy_job_and_valid_progress(queue_db):
    first = queue.enqueue(Job.Kind.INTEGRITY_CHECK, {"value": 1})
    queue.claim_next(queue.acquire_worker())
    with pytest.raises(IntegrityError), transaction.atomic():
        Job.objects.create(
            kind=Job.Kind.OCR, status=Job.Status.RUNNING, lease_owner=uuid4(), lease_expires_at=timezone.now()
        )
    with pytest.raises(IntegrityError), transaction.atomic():
        Job.objects.filter(pk=first.pk).update(progress=101)


def test_worker_success_and_sanitized_failure_without_retry(queue_db, monkeypatch, tmp_path):
    def success(ctx):
        assert ctx.payload == {"value": 1}
        ctx.checkpoint(50)

    monkeypatch.setitem(queue.HANDLERS, Job.Kind.INTEGRITY_CHECK, queue.Handler(validate_synthetic, success))
    job = queue.enqueue(Job.Kind.INTEGRITY_CHECK, {"value": 1})
    worker.run_worker(tmp_path / "worker.lock", once=True)
    job.refresh_from_db()
    assert job.status == Job.Status.SUCCEEDED and job.attempt == 1

    def failure(ctx):
        raise RuntimeError("synthetic secret exception")

    monkeypatch.setitem(queue.HANDLERS, Job.Kind.INTEGRITY_CHECK, queue.Handler(validate_synthetic, failure))
    failed = queue.enqueue(Job.Kind.INTEGRITY_CHECK, {"value": 1})
    worker.run_worker(tmp_path / "worker.lock", once=True)
    failed.refresh_from_db()
    assert failed.status == Job.Status.FAILED and failed.error_code == "HANDLER_FAILED"
    worker.run_worker(tmp_path / "worker.lock", once=True)
    failed.refresh_from_db()
    assert failed.attempt == 1


def test_print_uncertainty_requires_review_and_never_retries(queue_db, monkeypatch, tmp_path):
    calls = []

    def uncertain(ctx):
        calls.append(ctx.job_id)
        raise TimeoutError("synthetic printer acceptance unknown")

    monkeypatch.setitem(queue.HANDLERS, Job.Kind.PRINT, queue.Handler(validate_synthetic, uncertain))
    job = queue.enqueue(Job.Kind.PRINT, {"value": 1})
    worker.run_worker(tmp_path / "worker.lock", once=True)
    worker.run_worker(tmp_path / "worker.lock", once=True)
    job.refresh_from_db()
    assert job.status == Job.Status.REVIEW_REQUIRED
    assert job.error_code == "PRINT_ACCEPTANCE_UNKNOWN" and calls == [job.pk]


def test_os_lock_rejects_another_process_until_release(tmp_path):
    path = tmp_path / "worker.lock"
    script = (
        "from pathlib import Path; from core.locking import ProcessLock; import sys\n"
        "with ProcessLock(Path(sys.argv[1])): pass"
    )
    with ProcessLock(path):
        result = subprocess.run([sys.executable, "-c", script, str(path)], capture_output=True, timeout=10)
        assert result.returncode != 0
    subprocess.run([sys.executable, "-c", script, str(path)], check=True, timeout=10)


def test_worker_command_requires_explicit_role(monkeypatch):
    from config.env import env

    monkeypatch.setattr("apps.jobs.management.commands.run_worker.env", replace(env, service="web"))
    with pytest.raises(CommandError, match="NOTENARCHIV_SERVICE=worker"):
        call_command("run_worker", once=True)


def test_old_attempt_number_is_fenced_after_an_explicit_new_attempt(queue_db):
    job = queue.enqueue(Job.Kind.INTEGRITY_CHECK, {"value": 1})
    lease = queue.acquire_worker()
    old = queue.claim_next(lease)
    queue.finish(old)
    # Simulate a future authorized recovery transition; WP-05a exposes no requeue API.
    Job.objects.filter(pk=job.pk).update(status=Job.Status.QUEUED, finished_at=None, progress=0)
    current = queue.claim_next(lease)
    assert current.number == 2
    with pytest.raises(queue.StaleAttempt):
        queue.finish(old)
    with pytest.raises(queue.StaleAttempt):
        queue.heartbeat(lease, old, progress=99)
    job.refresh_from_db()
    assert job.status == Job.Status.RUNNING and job.progress == 0 and job.attempt == 2


def test_job_expiry_fences_completion_even_with_a_fresh_worker(queue_db):
    job = queue.enqueue(Job.Kind.INTEGRITY_CHECK, {"value": 1})
    lease = queue.acquire_worker()
    attempt = queue.claim_next(lease)
    Job.objects.filter(pk=job.pk).update(lease_expires_at=timezone.now() - timedelta(seconds=1))
    assert queue.worker_is_healthy()
    with pytest.raises(queue.StaleAttempt):
        queue.finish(attempt)


def test_missing_handlers_and_changed_payload_fail_before_execution(queue_db, monkeypatch, tmp_path):
    job = queue.enqueue(Job.Kind.INTEGRITY_CHECK, {"value": 1})
    monkeypatch.setattr(queue, "HANDLERS", {})
    worker.run_worker(tmp_path / "worker.lock", once=True)
    job.refresh_from_db()
    assert job.status == Job.Status.FAILED and job.error_code == "HANDLER_UNAVAILABLE"
    monkeypatch.setitem(queue.HANDLERS, Job.Kind.INTEGRITY_CHECK, queue.Handler(validate_synthetic, lambda ctx: None))
    invalid = queue.enqueue(Job.Kind.INTEGRITY_CHECK, {"value": 1})
    Job.objects.filter(pk=invalid.pk).update(payload={"private": "synthetic invalid payload"})
    worker.run_worker(tmp_path / "worker.lock", once=True)
    invalid.refresh_from_db()
    assert invalid.status == Job.Status.FAILED and invalid.error_code == "PAYLOAD_INVALID"


@pytest.mark.parametrize("interval", [0, 11, float("nan"), float("inf")])
def test_invalid_worker_intervals_fail_clearly(monkeypatch, interval):
    from config.env import env

    monkeypatch.setattr("apps.jobs.management.commands.run_worker.env", replace(env, service="worker"))
    with pytest.raises(CommandError, match="poll-seconds"):
        call_command("run_worker", poll_seconds=interval)
