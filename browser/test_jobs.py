"""Actual worker -> browser cancellation -> stopped child -> terminal state."""

import subprocess
import sys
import threading
import time
from datetime import timedelta
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import connections
from django.utils import timezone

from apps.jobs.models import Job, WorkerLease
from apps.jobs.services import queue, worker
from tests.test_queue import validate_synthetic


@pytest.mark.django_db(transaction=True)
def test_real_job_lifecycle_in_browser(settings, tmp_path, request, monkeypatch):
    settings.DEBUG_MODE = False
    settings.STATIC_ROOT = tmp_path / "staticfiles"
    call_command("collectstatic", interactive=False, verbosity=0)
    get_user_model().objects.create_user("synthetic-jobs", password="Synthetic-browser-135")
    WorkerLease.objects.get_or_create(pk=1)
    pulse = tmp_path / "synthetic-child-pulse"

    def process(ctx):
        if ctx.payload["value"] == 3:
            raise RuntimeError("synthetic-private-exception-and-ocr")
        if ctx.payload["value"] == 1:
            ctx.checkpoint(40)
            script = (
                "import pathlib,sys,time; p=pathlib.Path(sys.argv[1]); "
                "exec('while True:\\n p.write_text(str(time.monotonic()))\\n time.sleep(.02)')"
            )
            ctx.run_process([sys.executable, "-c", script, str(pulse)], timeout=30)

    monkeypatch.setitem(queue.HANDLERS, Job.Kind.INTEGRITY_CHECK, queue.Handler(validate_synthetic, process))
    lock = tmp_path / "worker.lock"
    # Use the same canonical lock as production for file-backed browser DBs.
    name = str(connections["default"].settings_dict["NAME"])
    if name != ":memory:" and not name.startswith("file:"):
        lock = Path(name).resolve().parent / "worker.lock"
    completed = queue.enqueue(Job.Kind.INTEGRITY_CHECK, {"value": 2})
    worker.run_worker(lock, once=True)
    failed = queue.enqueue(Job.Kind.INTEGRITY_CHECK, {"value": 3})
    worker.run_worker(lock, once=True)
    queued = queue.enqueue(Job.Kind.INTEGRITY_CHECK, {"value": 2})
    Job.objects.filter(pk=queued.pk).update(available_at=timezone.now() + timedelta(days=1))
    active = queue.enqueue(Job.Kind.INTEGRITY_CHECK, {"value": 1})
    shutdown, errors = threading.Event(), []

    def run():
        try:
            worker.run_worker(lock, once=True, shutdown=shutdown)
        except Exception as error:
            errors.append(error)
        finally:
            connections.close_all()

    server = request.getfixturevalue("live_server")
    thread = threading.Thread(target=run)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not pulse.exists() and time.monotonic() < deadline and thread.is_alive():
            time.sleep(0.05)
        assert pulse.exists(), errors
        subprocess.run(
            [
                "node",
                str(Path(__file__).with_name("jobs.cjs")),
                server.url,
                str(active.pk),
                str(completed.pk),
                str(failed.pk),
            ],
            check=True,
            timeout=60,
        )
    finally:
        shutdown.set()
        thread.join(timeout=10)
    assert not thread.is_alive() and not errors
    active.refresh_from_db()
    assert active.status == "CANCELLED" and active.finished_at
    before = pulse.read_bytes()
    time.sleep(0.15)
    assert pulse.read_bytes() == before
