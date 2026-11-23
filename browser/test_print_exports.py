"""Real browser print authorization, local PDF.js preview and completed download."""

import os
import subprocess
import threading
from pathlib import Path

import pytest
from django.core.management import call_command
from django.db import connections

from apps.exports.models import GenerationRun
from apps.exports.snapshot_services import authorize
from apps.jobs.models import WorkerLease
from apps.jobs.services.worker import run_worker
from apps.projects.models import Project
from tests.test_editions import edition_inputs as _edition
from tests.test_generation_snapshots import permission
from tests.test_resolution import resolver_inputs as _resolution

edition_inputs = _edition
resolver_inputs = _resolution


@pytest.mark.skipif(os.name != "posix", reason="Actual print publication requires POSIX")
@pytest.mark.django_db(transaction=True)
def test_print_preview_download_browser(resolver_inputs, settings, tmp_path, request):
    Project.objects.filter(pk=resolver_inputs[1].pk).update(layout="REGULAR")
    actor = resolver_inputs[0]
    actor.set_password("Synthetic-print-135")
    actor.save()
    for setting, name in (("SOURCE_DIR", "raw"), ("EXPORT_DIR", "export")):
        path = tmp_path / name
        path.mkdir()
        setattr(settings, setting, path)
    settings.PROCESSED_DIR.mkdir(exist_ok=True)
    settings.STATIC_ROOT = tmp_path / "static"
    call_command("collectstatic", interactive=False, verbosity=0)
    WorkerLease.objects.get_or_create(pk=1)
    old = authorize(**permission(resolver_inputs))
    lock = Path(connections["default"].settings_dict["NAME"]).parent / "worker.lock"
    run_worker(lock, once=True)
    stop, errors = threading.Event(), []

    def worker():
        try:
            run_worker(lock, poll_seconds=0.1, shutdown=stop)
        except Exception as exc:
            errors.append(exc)
        finally:
            connections.close_all()

    server = request.getfixturevalue("live_server")
    thread = threading.Thread(target=worker)
    thread.start()
    try:
        subprocess.run(
            ["node", str(Path(__file__).with_name("print_exports.cjs")), server.url, str(old.pk)],
            check=True,
            timeout=120,
        )
    finally:
        stop.set()
        thread.join(timeout=10)
    assert not errors and not thread.is_alive()
    runs = list(GenerationRun.objects.select_related("job", "snapshot"))
    assert len(runs) == 2 and all(r.job.status == "SUCCEEDED" for r in runs)
