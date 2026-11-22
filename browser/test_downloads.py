"""Browser direct PDF/ZIP selection without a project and unchanged PDF bytes."""

import hashlib
import subprocess
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from apps.archive import models as m
from apps.archive import services as s
from apps.catalog import models as c
from tests.archive_fixtures import PAGE
from tests.pdf_fixtures import A3, A4, pdf
from tests.test_archive_workflow import confirm, draft, receipt


@pytest.mark.django_db(transaction=True)
def test_direct_archive_pdf_and_zip_in_browser(settings, tmp_path, request):
    settings.STATIC_ROOT = tmp_path / "static"
    settings.CURATED_DIR = tmp_path / "clean"
    settings.DIAGNOSTIC_LOG_DIR = tmp_path / "data" / "logs"
    settings.DIAGNOSTIC_LOG_DIR.parent.mkdir()
    call_command("collectstatic", interactive=False, verbosity=0)
    actor = get_user_model().objects.create_user("downloads-browser", password="Synthetic-downloads-135")
    arr = c.Arrangement.objects.create(work=c.Work.objects.create(title="Synthetic direct archive"))
    variant = c.InstrumentVariant.objects.create(name="Posaune", clef="BASS")
    parts = [c.Part.objects.create(instrument=variant, code=str(n)) for n in (2, 3)]
    folder = m.SourceFolder.objects.create(relative_path="Synthetic")
    identifiers, hashes, before = [], [], {}
    for index in (1, 2):
        data = pdf(sizes=(A4, A3), text=bool(index % 2))
        pages = [
            PAGE,
            {**PAGE, "media_box": [0, 0, *A3], "crop_box": [0, 0, *A3], "width_points": A3[0], "height_points": A3[1]},
        ]
        digest = hashlib.sha256(data).hexdigest()
        version, _ = s.observe_version(
            folder.pk, f"Synthetic/{index}.pdf", sha256=digest, byte_size=len(data), pdf_state="VALID", page_info=pages
        )
        file, _ = receipt(s.register_base(version.pk, f"_Ungeprueft/{index}.pdf"))
        file = confirm(file, draft(file, actor, arr, parts), actor, path=f"Synthetic/{index}.pdf")
        path = settings.CURATED_DIR / file.relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        identifiers.append(str(file.pk))
        hashes.append(digest)
        before[path] = data
    server = request.getfixturevalue("live_server")
    subprocess.run(
        ["node", str(Path(__file__).with_name("downloads.cjs")), server.url, str(arr.pk), *identifiers, *hashes],
        check=True,
        timeout=90,
    )
    assert all(path.read_bytes() == data for path, data in before.items())
