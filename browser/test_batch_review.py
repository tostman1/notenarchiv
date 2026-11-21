"""Real browser per-file inspections and multi-file batch publication on Linux."""

import hashlib
import os
import subprocess
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import connections

from apps.archive import models as m
from apps.archive.services import observe_version, register_base
from apps.catalog import models as c
from apps.jobs.models import Job, WorkerLease
from apps.jobs.services.worker import run_worker
from tests.archive_fixtures import PAGE
from tests.pdf_fixtures import pdf
from tests.test_archive_workflow import receipt


@pytest.mark.django_db(transaction=True)
def test_individual_navigation_inspection_then_batch_in_browser(settings, tmp_path, request):
    settings.STATIC_ROOT = tmp_path / "static"
    for setting, name in (
        ("SOURCE_DIR", "raw"),
        ("CURATED_DIR", "clean"),
        ("PROCESSED_DIR", "processed"),
        ("STATUS_DIR", "status"),
    ):
        path = tmp_path / name
        path.mkdir()
        setattr(settings, setting, path)
    call_command("collectstatic", interactive=False, verbosity=0)
    WorkerLease.objects.get_or_create(pk=1)
    actor = get_user_model().objects.create_user("batch-browser", password="Synthetic-batch-135")
    work = c.Work.objects.create(title="Synthetic batch")
    arrangement = c.Arrangement.objects.create(work=work)
    variant = c.InstrumentVariant.objects.create(name="Synthetic batch", clef="BASS")
    part = c.Part.objects.create(instrument=variant, code="1")
    folder = m.SourceFolder.objects.create(relative_path="Synthetic batch")
    identifiers = []
    data = pdf()
    for number in (1, 2):
        version, _ = observe_version(
            folder.pk,
            f"Synthetic batch/{number}.pdf",
            sha256=hashlib.sha256(data).hexdigest(),
            byte_size=len(data),
            pdf_state="VALID",
            page_info=[PAGE],
        )
        file, _ = receipt(register_base(version.pk, f"_Ungeprueft/{number}.pdf"))
        path = settings.CURATED_DIR / file.relative_path
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(data)
        identifiers.append(str(file.pk))
    server = request.getfixturevalue("live_server")
    script = str(Path(__file__).with_name("batch_review.cjs"))
    subprocess.run(
        [
            "node",
            script,
            server.url,
            str(arrangement.pk),
            str(variant.pk),
            str(part.pk),
            *identifiers,
            "approve" if os.name == "posix" else "inspect",
        ],
        check=True,
        timeout=90,
    )
    assert m.ReviewInspection.objects.filter(reviewer=actor).count() == 2
    if os.name == "posix":
        assert Job.objects.filter(status="QUEUED").count() == 2
        lock = Path(connections["default"].settings_dict["NAME"]).parent / "worker.lock"
        run_worker(lock, once=True)
        run_worker(lock, once=True)
        assert m.ArchiveFile.objects.usable().count() == 2
        assert len(set(m.ArchiveFile.objects.values_list("relative_path", flat=True))) == 2
