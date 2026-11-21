"""Actual browser index submission/cancellation; Linux copy/STATUS end-to-end."""

import os
import subprocess
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import connections

from apps.archive import models as m
from apps.jobs.models import Job
from apps.jobs.services.worker import run_worker
from tests.publication_scenario import synthetic_pdf
from tests.test_indexing import raw_snapshot


@pytest.mark.django_db(transaction=True)
def test_index_submission_status_and_review_queue_in_browser(settings, tmp_path, request):
    settings.DEBUG_MODE = False
    settings.STATIC_ROOT = tmp_path / "staticfiles"
    for setting, name in (
        ("SOURCE_DIR", "raw"),
        ("CURATED_DIR", "clean"),
        ("PROCESSED_DIR", "processed"),
        ("STATUS_DIR", "status"),
    ):
        path = tmp_path / name
        path.mkdir()
        setattr(settings, setting, path)
    selected = settings.SOURCE_DIR / "Synthetic selected"
    selected.mkdir()
    (selected / "unknown.pdf").write_bytes(synthetic_pdf())
    before = raw_snapshot(settings.SOURCE_DIR)
    call_command("collectstatic", interactive=False, verbosity=0)
    get_user_model().objects.create_user("index-browser", password="Synthetic-index-135")
    server = request.getfixturevalue("live_server")
    script = str(Path(__file__).with_name("indexing.cjs"))
    subprocess.run(["node", script, server.url, "queue"], check=True, timeout=60)
    assert Job.objects.filter(kind="INDEX_SCAN", status="CANCELLED").count() == 1
    assert m.IndexScan.objects.get(job__status="QUEUED").selected_path == "Synthetic selected"
    if os.name == "posix":
        lock = Path(connections["default"].settings_dict["NAME"]).parent / "worker.lock"
        run_worker(lock, once=True)
        job = Job.objects.get(status="SUCCEEDED", kind="INDEX_SCAN")
        assert job.index_scan.completed
        folder = m.SourceFolder.objects.get(relative_path="Synthetic selected")
        subprocess.run(["node", script, server.url, "complete", str(folder.pk)], check=True, timeout=60)
        assert (settings.STATUS_DIR / folder.relative_path / "INDEXSTATUS.json").exists()
        assert not m.ArchiveFile.objects.usable().exists() and m.ReviewInspection.objects.count() == 0
    assert raw_snapshot(settings.SOURCE_DIR) == before
