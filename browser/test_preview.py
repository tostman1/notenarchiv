"""Real PDF.js canvas/worker acceptance with synthetic pending/confirmed CLEAN."""

import hashlib
import subprocess
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from apps.archive import models as m
from apps.archive import services
from apps.catalog import models as catalog
from tests.archive_fixtures import PAGE
from tests.pdf_fixtures import A3, A4, pdf
from tests.test_archive_workflow import confirm, draft, receipt


@pytest.mark.django_db(transaction=True)
def test_local_pdfjs_pending_and_confirmed_preview(settings, tmp_path, request):
    settings.STATIC_ROOT = tmp_path / "static"
    settings.CURATED_DIR = tmp_path / "clean"
    settings.DIAGNOSTIC_LOG_DIR = tmp_path / "logs"
    call_command("collectstatic", interactive=False, verbosity=0)
    actor = get_user_model().objects.create_user("preview-browser", password="Synthetic-preview-135")
    folder = m.SourceFolder.objects.create(relative_path="Synthetic preview")
    identifiers = []
    for index, scan in enumerate((False, True)):
        data = pdf(sizes=(A4, A3), text=not scan, scan=scan, active=True)
        version, _created = services.observe_version(
            folder.pk,
            f"Synthetic preview/{index}.pdf",
            sha256=hashlib.sha256(data).hexdigest(),
            byte_size=len(data),
            mtime_ns=index,
            pdf_state="VALID",
            page_info=[
                PAGE,
                {
                    **PAGE,
                    "media_box": [0, 0, *A3],
                    "crop_box": [0, 0, *A3],
                    "width_points": A3[0],
                    "height_points": A3[1],
                },
            ],
        )
        file = services.register_base(version.pk, f"_Ungeprueft/{index}.pdf")
        file, _operation = receipt(file)
        if scan:
            work = catalog.Work.objects.create(title="Synthetic preview")
            arrangement = catalog.Arrangement.objects.create(work=work)
            instrument = catalog.InstrumentVariant.objects.create(name="Synthetic preview")
            part = catalog.Part.objects.create(instrument=instrument, code="1")
            file = confirm(file, draft(file, actor, arrangement, [part]), actor)
        path = settings.CURATED_DIR / file.relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        identifiers.append(str(file.pk))
    before = m.ReviewInspection.objects.count()
    server = request.getfixturevalue("live_server")
    subprocess.run(
        ["node", str(Path(__file__).with_name("preview.cjs")), server.url, *identifiers],
        check=True,
        timeout=90,
    )
    assert m.ReviewInspection.objects.count() == before
