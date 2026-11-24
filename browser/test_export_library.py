"""Browser library metadata, current targeted preflight and project-free archive PDF."""

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
from apps.projects.models import PartOverride, Project
from apps.projects.preflight_services import build_report, report_token
from tests.test_editions import edition_inputs as _edition
from tests.test_resolution import resolver_inputs as _resolution

edition_inputs = _edition
resolver_inputs = _resolution


@pytest.mark.skipif(os.name != "posix", reason="Real library publication requires POSIX")
@pytest.mark.django_db(transaction=True)
def test_export_library_browser(resolver_inputs, settings, tmp_path, request):
    actor, project, arr, parts, people, positions, first, *_ = resolver_inputs
    Project.objects.filter(pk=project.pk).update(layout="REGULAR")
    for person in people[1:]:
        for position in positions[:2]:
            PartOverride.objects.create(
                project=project,
                participant=person,
                position=position,
                desired_part=parts[1],
                edition=first.assignments.get(),
            )
    actor.set_password("Synthetic-library-135")
    actor.save()
    for setting, name in (("SOURCE_DIR", "raw"), ("EXPORT_DIR", "export")):
        path = tmp_path / name
        path.mkdir()
        setattr(settings, setting, path)
    settings.PROCESSED_DIR.mkdir(exist_ok=True)
    settings.STATIC_ROOT = tmp_path / "static"
    call_command("collectstatic", interactive=False, verbosity=0)
    WorkerLease.objects.get_or_create(pk=1)
    report = build_report(project.pk, participant_ids=[p.pk for p in people[1:]])
    authorize(
        project.pk,
        participant_ids=list(report.session.participants),
        position_ids=list(report.session.positions),
        token=report_token(report, actor),
        acknowledgements=[],
        actor=actor,
    )
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
            ["node", str(Path(__file__).with_name("export_library.cjs")), server.url, str(project.pk), str(first.pk)],
            check=True,
            timeout=150,
        )
    finally:
        stop.set()
        thread.join(timeout=10)
    assert not errors and not thread.is_alive()
    assert GenerationRun.objects.filter(snapshot__kind="ARCHIVE_NOTES", job__status="SUCCEEDED").exists()
