"""Actual browser current excerpt, contents-only and historical exact download."""

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
from apps.projects.models import PartOverride
from tests.test_editions import edition_inputs as _edition_fixture
from tests.test_resolution import resolver_inputs as _resolution_fixture

edition_inputs = _edition_fixture
resolver_inputs = _resolution_fixture


@pytest.mark.skipif(os.name != "posix", reason="Actual generated download requires POSIX publication")
@pytest.mark.django_db(transaction=True)
def test_project_export_browser(resolver_inputs, settings, tmp_path, request):
    actor, project, _arr, parts, people, positions, first, *_ = resolver_inputs
    actor.set_password("Synthetic-snapshot-135")
    actor.save()
    PartOverride.objects.create(
        project=project,
        participant=people[2],
        position=positions[0],
        desired_part=parts[1],
        edition=first.assignments.get(),
    )
    for setting, directory in (("SOURCE_DIR", "raw"), ("EXPORT_DIR", "export")):
        path = tmp_path / directory
        path.mkdir()
        setattr(settings, setting, path)
    settings.PROCESSED_DIR.mkdir(exist_ok=True)
    settings.STATIC_ROOT = tmp_path / "static"
    call_command("collectstatic", interactive=False, verbosity=0)
    server = request.getfixturevalue("live_server")
    WorkerLease.objects.get_or_create(pk=1)
    stop, errors = threading.Event(), []
    lock = Path(connections["default"].settings_dict["NAME"]).parent / "worker.lock"

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
                str(Path(__file__).with_name("project_exports.cjs")),
                server.url,
                str(project.pk),
                str(people[2].pk),
                str(positions[0].pk),
            ],
            check=True,
            timeout=120,
        )
    finally:
        stop.set()
        thread.join(timeout=10)
    assert not thread.is_alive() and not errors
    runs = list(GenerationRun.objects.select_related("job", "snapshot"))
    assert len(runs) == 3 and all(r.job.status == "SUCCEEDED" for r in runs)
    assert sorted(r.snapshot.kind for r in runs) == ["CONTENTS", "EXCERPT", "EXCERPT"]
    assert all(r.artifacts.get().manifest["page_count"] == 1 for r in runs)
