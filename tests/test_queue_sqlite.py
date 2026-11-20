"""Actual Django ORM races using independent connections to file-backed SQLite."""

import copy
import os
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from django.db import connections, transaction
from django.utils import timezone

from apps.jobs.models import Job, WorkerLease
from apps.jobs.services import queue, worker
from core.locking import ProcessLock
from tests.test_queue import validate_synthetic


@pytest.fixture()
def sqlite_queue(tmp_path, django_db_blocker, monkeypatch):
    aliases = ("queue_race_0", "queue_race_1")
    for alias in aliases:
        configuration = copy.deepcopy(connections["default"].settings_dict)
        configuration["NAME"] = str(tmp_path / "queue.sqlite3")
        configuration["OPTIONS"] = {}
        configuration["TEST"] = {}
        connections.databases[alias] = configuration
    monkeypatch.setattr(
        queue, "HANDLERS", {Job.Kind.INTEGRITY_CHECK: queue.Handler(validate_synthetic, lambda ctx: None)}
    )
    with django_db_blocker.unblock():
        try:
            with connections[aliases[0]].schema_editor() as editor:
                editor.create_model(Job)
                editor.create_model(WorkerLease)
            WorkerLease.objects.using(aliases[0]).create(pk=1)
            yield aliases
        finally:
            for alias in aliases:
                connections[alias].close()
                del connections[alias]
                del connections.databases[alias]


def test_thirty_independent_connection_races_have_exactly_one_worker_and_job(sqlite_queue):
    first, second = sqlite_queue
    with ThreadPoolExecutor(max_workers=2) as pool:
        for _round in range(30):
            Job.objects.using(first).all().delete()
            for value in (1, 2):
                queue.enqueue(Job.Kind.INTEGRITY_CHECK, {"value": value}, using=first)
            barrier = threading.Barrier(2, timeout=5)

            def compete(alias, barrier=barrier):
                try:
                    barrier.wait()
                    lease = queue.acquire_worker(using=alias)
                    return queue.claim_next(lease, using=alias) if lease else None
                finally:
                    connections[alias].close()

            results = [
                future.result(timeout=15) for future in [pool.submit(compete, alias) for alias in (first, second)]
            ]
            winners = [attempt for attempt in results if attempt]
            assert len(winners) == 1
            assert Job.objects.using(first).filter(status=Job.Status.RUNNING).count() == 1
            assert Job.objects.using(first).filter(status=Job.Status.QUEUED).count() == 1
            queue.finish(winners[0], using=second)
            assert queue.release_worker(winners[0].lease, using=first)


def test_same_lease_cannot_claim_two_jobs_across_connections(sqlite_queue):
    first, second = sqlite_queue
    for value in (1, 2):
        queue.enqueue(Job.Kind.INTEGRITY_CHECK, {"value": value}, using=first)
    lease = queue.acquire_worker(using=first)
    barrier = threading.Barrier(2, timeout=5)

    def compete(alias):
        try:
            barrier.wait()
            return queue.claim_next(lease, using=alias)
        finally:
            connections[alias].close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = [future.result(timeout=15) for future in [pool.submit(compete, alias) for alias in (first, second)]]
    assert sum(attempt is not None for attempt in results) == 1


@pytest.mark.parametrize("busy", [False, True])
def test_heartbeat_renews_independently_when_idle_or_busy(sqlite_queue, tmp_path, monkeypatch, busy):
    first, _second = sqlite_queue
    monkeypatch.setattr(queue, "HEARTBEAT_SECONDS", 0.05)
    beat, release, shutdown = threading.Event(), threading.Event(), threading.Event()
    errors = []
    original_heartbeat = queue.heartbeat

    def observe(lease, attempt=None, **kwargs):
        original_heartbeat(lease, attempt, **kwargs)
        if bool(attempt) is busy:
            beat.set()

    def handler(ctx):
        if not release.wait(5):
            raise TimeoutError("Synthetic test did not release the job")

    monkeypatch.setattr(queue, "heartbeat", observe)
    monkeypatch.setitem(queue.HANDLERS, Job.Kind.INTEGRITY_CHECK, queue.Handler(validate_synthetic, handler))
    if busy:
        queue.enqueue(Job.Kind.INTEGRITY_CHECK, {"value": 1}, using=first)

    def run():
        try:
            worker.run_worker(tmp_path / "worker.lock", once=busy, shutdown=shutdown, using=first)
        except Exception as exc:
            errors.append(exc)
        finally:
            connections.close_all()

    thread = threading.Thread(target=run)
    thread.start()
    try:
        assert beat.wait(5), "No independent heartbeat observed"
        lease = WorkerLease.objects.using(first).get(pk=1)
        assert lease.owner is not None and lease.heartbeat_at is not None
        if busy:
            job = Job.objects.using(first).get()
            assert job.status == Job.Status.RUNNING
            assert lease.heartbeat_at > job.started_at
    finally:
        shutdown.set()
        release.set()
        thread.join(timeout=10)
    assert not thread.is_alive() and not errors
    assert not queue.worker_is_healthy(using=first)


def test_actual_worker_command_rejects_duplicate_and_runs_after_release(sqlite_queue, tmp_path):
    first, _second = sqlite_queue
    environment = os.environ.copy()
    environment.update(
        {
            "NOTENARCHIV_PROFILE": "local",
            "NOTENARCHIV_SERVICE": "worker",
            "DEBUG_MODE": "FALSE",
            "DJANGO_SETTINGS_MODULE": "config.settings",
            "NOTENARCHIV_LOCAL_ROOT": str(tmp_path / "synthetic-roots"),
            "DATABASE_PATH": connections[first].settings_dict["NAME"],
        }
    )
    command = [sys.executable, "manage.py", "run_worker", "--once"]
    with ProcessLock(tmp_path / "worker.lock"):
        duplicate = subprocess.run(command, env=environment, capture_output=True, text=True, timeout=15)
        assert duplicate.returncode != 0
        assert "Worker stopped safely" in duplicate.stderr
    completed = subprocess.run(command, env=environment, capture_output=True, text=True, timeout=15)
    assert completed.returncode == 0, completed.stderr
    assert WorkerLease.objects.using(first).get(pk=1).owner is None


def test_debug_healthcheck_does_not_compete_for_worker_log(sqlite_queue, tmp_path):
    first, _second = sqlite_queue
    environment = os.environ.copy()
    environment.update(
        {
            "NOTENARCHIV_PROFILE": "local",
            "NOTENARCHIV_SERVICE": "worker",
            "DEBUG_MODE": "TRUE",
            "DJANGO_SETTINGS_MODULE": "config.settings",
            "NOTENARCHIV_LOCAL_ROOT": str(tmp_path / "synthetic-roots"),
            "DATABASE_PATH": connections[first].settings_dict["NAME"],
        }
    )
    running = subprocess.Popen(
        [sys.executable, "manage.py", "run_worker", "--poll-seconds", "0.1"],
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and running.poll() is None:
            if queue.worker_is_healthy(using=first):
                break
            time.sleep(0.05)
        assert running.poll() is None and queue.worker_is_healthy(using=first)
        health = subprocess.run(
            [sys.executable, "manage.py", "worker_healthcheck"],
            env=environment,
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert health.returncode == 0, health.stderr
        assert "heartbeat is fresh" in health.stdout
        path = tmp_path / "synthetic-roots" / "logs" / "worker.debug.log"
        assert path.is_file()
        assert running.poll() is None
    finally:
        # This synthetic idle worker has no handler/subprocess or published output.
        running.terminate()
        running.communicate(timeout=10)


def test_lease_expiring_while_waiting_for_sqlite_write_lock_cannot_be_renewed(sqlite_queue):
    first, second = sqlite_queue
    job = queue.enqueue(Job.Kind.INTEGRITY_CHECK, {"value": 1}, using=first)
    lease = queue.acquire_worker(using=first)
    entered = threading.Event()
    outcomes = []

    def observe(execute, sql, params, many, context):
        if sql.startswith("UPDATE"):
            entered.set()
        return execute(sql, params, many, context)

    def waiting_claim():
        try:
            with connections[second].execute_wrapper(observe):
                queue.claim_next(lease, using=second)
            outcomes.append("unexpected claim")
        except queue.StaleAttempt:
            outcomes.append("fenced")
        finally:
            connections[second].close()

    with transaction.atomic(using=first):
        expires = timezone.now() + timedelta(seconds=0.3)
        WorkerLease.objects.using(first).filter(pk=1).update(expires_at=expires)
        thread = threading.Thread(target=waiting_claim)
        thread.start()
        assert entered.wait(5)
        time.sleep(max(0, (expires - timezone.now()).total_seconds()) + 0.05)
    thread.join(timeout=10)
    assert not thread.is_alive() and outcomes == ["fenced"]
    assert Job.objects.using(first).get(pk=job.pk).status == Job.Status.QUEUED
