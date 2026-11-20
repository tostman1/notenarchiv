"""Actual process death and claim/cancel races over independent SQLite connections."""

import os
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from django.db import connections
from django.utils import timezone

from apps.jobs.models import AttemptRecord, Job, WorkerLease
from apps.jobs.services import lifecycle, queue, worker
from core.locking import ProcessLock
from tests.test_queue import validate_synthetic
from tests.test_queue_sqlite import sqlite_queue as _sqlite_fixture

sqlite_queue = _sqlite_fixture


def test_real_crash_before_intent_acknowledgement_recovers_once(sqlite_queue, tmp_path, monkeypatch):
    alias, _second = sqlite_queue
    job = queue.enqueue(Job.Kind.INTEGRITY_CHECK, {"value": 1}, using=alias)
    target = tmp_path / "synthetic-result"
    environment = os.environ.copy()
    environment.update(
        DJANGO_SETTINGS_MODULE="config.settings",
        NOTENARCHIV_PROFILE="local",
        NOTENARCHIV_SERVICE="worker",
        DEBUG_MODE="FALSE",
        NOTENARCHIV_LOCAL_ROOT=str(tmp_path / "synthetic-roots"),
        DATABASE_PATH=connections[alias].settings_dict["NAME"],
    )
    script = """
import django,os,sys
from pathlib import Path
django.setup()
from apps.jobs.services import queue,worker
def run(ctx):
    def apply():
        Path(sys.argv[1]).write_text('one verified synthetic result')
        os._exit(23)
    ctx.publish('result',{},apply)
queue.HANDLERS['INTEGRITY_CHECK']=queue.Handler(lambda value:value,run,True,2)
worker.run_worker(Path(sys.argv[1]).parent/'worker.lock',once=True)
"""
    result = subprocess.run(
        [sys.executable, "-c", script, str(target)], env=environment, capture_output=True, timeout=15
    )
    assert result.returncode == 23, result.stderr
    row = Job.objects.using(alias).get(pk=job.pk)
    old_lease = WorkerLease.objects.using(alias).get(pk=1)
    old = queue.Attempt(
        row.pk, queue.Lease(row.lease_owner, old_lease.generation), row.attempt, row.kind, row.payload, 1
    )
    assert row.status == "RUNNING" and row.operations.using(alias).get().state == "PENDING"
    assert target.read_text() == "one verified synthetic result"

    def run(ctx):
        assert ctx.publish("result", {}, lambda: pytest.fail("Crash result must not be published twice")) == {
            "verified": True
        }

    def reconcile(ctx, intent):
        ctx.checkpoint()
        return "APPLIED", {"verified": target.read_text() == "one verified synthetic result"}

    monkeypatch.setitem(
        queue.HANDLERS, Job.Kind.INTEGRITY_CHECK, queue.Handler(validate_synthetic, run, True, 2, reconcile)
    )
    worker.run_worker(tmp_path / "worker.lock", once=True, using=alias)
    with pytest.raises(queue.StaleAttempt):
        queue.finish(old, using=alias)
    Job.objects.using(alias).filter(pk=job.pk).update(available_at=timezone.now())
    worker.run_worker(tmp_path / "worker.lock", once=True, using=alias)
    row.refresh_from_db(using=alias)
    assert row.status == "SUCCEEDED" and row.attempt == 2 and row.history.using(alias).count() == 2


def test_wrong_lock_cannot_take_over_a_live_database_lease(sqlite_queue, tmp_path):
    alias, _second = sqlite_queue
    lease = queue.acquire_worker(using=alias)
    with ProcessLock(tmp_path / "different.lock") as authority, pytest.raises(RuntimeError, match="canonical"):
        lifecycle.acquire_owned(authority, using=alias)
    assert WorkerLease.objects.using(alias).get(pk=1).owner == lease.owner


def test_cancel_and_claim_races_never_start_a_cancelled_job(sqlite_queue):
    first, second = sqlite_queue
    for _round in range(20):
        AttemptRecord.objects.using(first).all().delete()
        Job.objects.using(first).all().delete()
        job = queue.enqueue(Job.Kind.INTEGRITY_CHECK, {"value": 1}, using=first)
        lease = queue.acquire_worker(using=first)
        barrier = threading.Barrier(2, timeout=5)

        def compete(alias, action, barrier=barrier):
            try:
                barrier.wait()
                return action(alias)
            finally:
                connections[alias].close()

        with ThreadPoolExecutor(max_workers=2) as pool:
            claim = pool.submit(compete, first, lambda alias, lease=lease: queue.claim_next(lease, using=alias))
            cancel = pool.submit(
                compete, second, lambda alias, job_id=job.pk: lifecycle.request_cancel(job_id, using=alias)
            )
            attempt, accepted = claim.result(timeout=10), cancel.result(timeout=10)
        assert accepted
        row = Job.objects.using(first).get(pk=job.pk)
        if attempt:
            assert row.status == "RUNNING" and row.cancel_requested
            queue.finish(attempt, using=second)
        else:
            assert row.status == "CANCELLED" and row.attempt == 0
        assert Job.objects.using(first).get(pk=job.pk).status == "CANCELLED"
        assert queue.release_worker(lease, using=first)
