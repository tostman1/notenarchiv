"""Actual local browser preference/reset and pinned manual selection."""

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
def test_preference_changes_preserve_explicit_choice_in_browser(settings, tmp_path, request):
    settings.STATIC_ROOT = tmp_path / "static"
    settings.CURATED_DIR = tmp_path / "clean"
    call_command("collectstatic", interactive=False, verbosity=0)
    actor = get_user_model().objects.create_user("editions-browser", password="Synthetic-editions-135")
    arrangement = c.Arrangement.objects.create(work=c.Work.objects.create(title="Synthetic versions"))
    part = c.Part.objects.create(instrument=c.InstrumentVariant.objects.create(name="Posaune", clef="BASS"), code="2")
    folder = m.SourceFolder.objects.create(relative_path="Synthetic")
    assignments, before = [], {}
    for index in (1, 2):
        data = pdf(text=bool(index % 2))
        version, _ = s.observe_version(
            folder.pk,
            f"Synthetic/{index}.pdf",
            sha256=hashlib.sha256(data).hexdigest(),
            byte_size=len(data),
            pdf_state="VALID",
            page_info=[PAGE],
        )
        file, _ = receipt(s.register_base(version.pk, f"_Ungeprueft/{index}.pdf"))
        file = confirm(file, draft(file, actor, arrangement, [part]), actor, path=f"Synthetic/{index}.pdf")
        path = settings.CURATED_DIR / file.relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        assignments.append(file.assignments.get())
        before[path] = data
    server = request.getfixturevalue("live_server")
    subprocess.run(
        [
            "node",
            str(Path(__file__).with_name("editions.cjs")),
            server.url,
            str(arrangement.pk),
            str(part.pk),
            *[str(item.pk) for item in assignments],
            str(assignments[0].archive_file_id),
        ],
        check=True,
        timeout=90,
    )
    assert m.PreferredEdition.objects.get().assignment_id is None
    assert m.EditionPreferenceChange.objects.count() == 3
    assert all(path.read_bytes() == data for path, data in before.items())
