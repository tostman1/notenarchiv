"""Real browser uses the same inspected edition in matrix and signed preflight."""

import subprocess
from pathlib import Path

import pytest
from django.core.management import call_command

from apps.archive.content_preferences import set_content_preference
from apps.archive.content_services import confirm_content, inspect_content, propose_content
from apps.archive.models import ContentEdition, LogicalPage, LogicalPageRevision
from apps.exports.models import GenerationRun
from tests.test_editions import edition_inputs as legacy_inputs
from tests.test_resolution import resolver_inputs as project_inputs

edition_inputs = legacy_inputs
resolver_inputs = project_inputs


@pytest.mark.django_db(transaction=True)
def test_project_content_browser_authorizes_exact_cell(resolver_inputs, settings, tmp_path, request):
    actor, project, arrangement, parts, people, positions, file, *_ = resolver_inputs
    logical = LogicalPage.objects.create()
    page = LogicalPageRevision.objects.create(
        logical_page=logical, number=1, source_page=file.source_version.pages.first()
    )
    edition = ContentEdition.objects.create(arrangement=arrangement, part=parts[1])
    revision = propose_content(edition.pk, expected_number=0, inputs=[(page.pk, file.pk)])
    inspection = inspect_content(
        revision.pk, actor=actor, expected_fingerprint=revision.fingerprint, visually_reviewed=True
    )
    confirm_content(inspection.pk, actor=actor)
    arrangement.refresh_from_db()
    set_content_preference(arrangement.pk, parts[1].pk, edition.pk, actor=actor, expected_revision=arrangement.revision)
    actor.set_password("Synthetic-project-content-135")
    actor.save()
    settings.STATIC_ROOT = tmp_path / "static"
    call_command("collectstatic", interactive=False, verbosity=0)
    server = request.getfixturevalue("live_server")
    subprocess.run(
        [
            "node",
            str(Path(__file__).with_name("project_content.cjs")),
            server.url,
            str(project.pk),
            str(people[1].pk),
            str(positions[0].pk),
            str(edition.pk),
        ],
        check=True,
        timeout=90,
    )
    run = GenerationRun.objects.get()
    assert run.job.status == "QUEUED" and run.snapshot.payload["schema"] == 3
    assert run.snapshot.project_content_inputs.count() == 1 and not run.snapshot.inputs.exists()
    assert run.snapshot.payload["cells"][0]["content"]["edition_id"] == str(edition.pk)
