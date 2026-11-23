"""Browser preflight to real worker, verified complete PDF download (Linux)."""

import os
import subprocess
import threading
from pathlib import Path

import pytest
from django.core.management import call_command
from django.db import connections

from apps.exports.models import GenerationRun
from apps.jobs.models import WorkerLease
from apps.jobs.services.worker import run_worker
from tests.test_editions import edition_inputs as _edition_fixture
from tests.test_resolution import resolver_inputs as _resolution_fixture

edition_inputs = _edition_fixture
resolver_inputs = _resolution_fixture


@pytest.mark.skipif(os.name != "posix", reason="Real generated publication requires POSIX")
@pytest.mark.django_db(transaction=True)
def test_personal_folder_browser_download(resolver_inputs, settings, tmp_path, request):
    actor, project, _arr, _parts, people, _positions, *_ = resolver_inputs
    actor.set_password("Synthetic-snapshot-135")
    actor.save()
    from apps.projects.models import Project

    Project.objects.filter(pk=project.pk).update(cover_enabled=False)
    for setting, directory in (("SOURCE_DIR", "raw"), ("EXPORT_DIR", "export")):
        path = tmp_path / directory
        path.mkdir()
        setattr(settings, setting, path)
    data = tmp_path / "data"
    data.mkdir(mode=0o700)
    settings.PROCESSED_DIR.mkdir(exist_ok=True)
    settings.DIAGNOSTIC_LOG_DIR = data / "logs"
    settings.STATIC_ROOT = tmp_path / "static"
    call_command("collectstatic", interactive=False, verbosity=0)
    server = request.getfixturevalue("live_server")
    WorkerLease.objects.get_or_create(pk=1)
    lock = Path(connections["default"].settings_dict["NAME"]).parent / "worker.lock"
    stop, errors = threading.Event(), []

    def worker():
        try:
            run_worker(lock, poll_seconds=0.1, shutdown=stop)
        except Exception as exc:
            errors.append(exc)
        finally:
            connections.close_all()

    thread = threading.Thread(target=worker)
    thread.start()
    try:
        subprocess.run(
            [
                "node",
                str(Path(__file__).with_name("personal_generation.cjs")),
                server.url,
                str(project.pk),
                str(people[0].pk),
            ],
            check=True,
            timeout=90,
        )
    finally:
        stop.set()
        thread.join(timeout=10)
    assert not thread.is_alive() and not errors
    run = GenerationRun.objects.get()
    assert run.job.status == "SUCCEEDED" and run.artifacts.get().manifest["page_count"] == 3
