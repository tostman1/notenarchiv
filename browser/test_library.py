"""Live library search and completeness/expected-template workflow in a browser."""

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
from tests.pdf_fixtures import pdf
from tests.test_archive_workflow import confirm, draft, receipt


@pytest.mark.django_db(transaction=True)
def test_library_live_search_and_completeness_in_browser(settings, tmp_path, request):
    settings.STATIC_ROOT = tmp_path / "static"
    settings.CURATED_DIR = tmp_path / "clean"
    call_command("collectstatic", interactive=False, verbosity=0)
    actor = get_user_model().objects.create_user("library-browser", password="Synthetic-library-135")
    arrangements = []
    for title in ("ABBA Medley", "Abel Tasman", "Fuchsgraben Polka", "Other"):
        arrangements.append(c.Arrangement.objects.create(work=c.Work.objects.create(title=title)))
    c.WorkAlias.objects.create(work=arrangements[-1].work, alias="Ab alias")
    variant = c.InstrumentVariant.objects.create(name="Synthetic library", clef="BASS")
    parts = [c.Part.objects.create(instrument=variant, code=str(n)) for n in (1, 2)]
    template = c.InstrumentationTemplate.objects.create(name="Synthetic library template")
    for part in parts:
        c.TemplatePart.objects.create(template=template, part=part, required=True)
    folder = m.SourceFolder.objects.create(relative_path="Synthetic library")
    data = pdf()
    version, _ = s.observe_version(
        folder.pk,
        "Synthetic library/scan.pdf",
        sha256=hashlib.sha256(data).hexdigest(),
        byte_size=len(data),
        pdf_state="VALID",
        page_info=[PAGE],
    )
    file, _ = receipt(s.register_base(version.pk, "_Ungeprueft/library.pdf"))
    file = confirm(file, draft(file, actor, arrangements[0], parts[:1]), actor)
    path = settings.CURATED_DIR / file.relative_path
    path.parent.mkdir(parents=True)
    path.write_bytes(data)
    before = path.read_bytes()
    server = request.getfixturevalue("live_server")
    subprocess.run(
        ["node", str(Path(__file__).with_name("library.cjs")), server.url, str(arrangements[0].pk), str(template.pk)],
        check=True,
        timeout=90,
    )
    arrangements[0].refresh_from_db()
    assert arrangements[0].expectations_defined and arrangements[0].expected_parts.count() == 2
    assert m.ArchiveFile.objects.usable().count() == 1 and path.read_bytes() == before
