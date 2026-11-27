"""Opt-in signed preflight creates exact historical project content pins."""

import pytest
from django.core.exceptions import ValidationError

from apps.archive.content_geometry_services import append_logical_page
from apps.archive.content_preferences import set_content_preference
from apps.archive.content_services import confirm_content, inspect_content, propose_content
from apps.archive.models import ContentEdition, LogicalPage, LogicalPageRevision
from apps.exports.snapshot_services import authorize, load_pinned_inputs
from apps.projects.preflight_services import build_report, report_token
from tests.test_editions import edition_inputs as legacy_inputs
from tests.test_resolution import resolver_inputs as project_inputs

edition_inputs = legacy_inputs
resolver_inputs = project_inputs


@pytest.mark.django_db
def test_signed_content_preflight_pins_current_selection_and_preserves_history(resolver_inputs):
    actor, project, arrangement, parts, people, positions, first, *_ = resolver_inputs
    logical = LogicalPage.objects.create()
    page = LogicalPageRevision.objects.create(
        logical_page=logical, number=1, source_page=first.source_version.pages.first()
    )
    edition = ContentEdition.objects.create(arrangement=arrangement, part=parts[1])
    revision = propose_content(edition.pk, expected_number=0, inputs=[(page.pk, first.pk)])
    inspection = inspect_content(
        revision.pk, actor=actor, expected_fingerprint=revision.fingerprint, visually_reviewed=True
    )
    confirm_content(inspection.pk, actor=actor)
    arrangement.refresh_from_db()
    set_content_preference(arrangement.pk, parts[1].pk, edition.pk, actor=actor, expected_revision=arrangement.revision)
    selection = {"participant_ids": [people[1].pk], "position_ids": [positions[0].pk], "include_content": True}
    report = build_report(project.pk, **selection)
    assert report.blocking == 0 and report.payload["schema"] == 3
    assert report.payload["cells"][0]["content"]["edition_id"] == str(edition.pk)
    token = report_token(report, actor)
    run = authorize(project.pk, **selection, token=token, acknowledgements=[], actor=actor, kind="EXCERPT")
    assert run.snapshot.project_content_inputs.count() == 1 and not run.snapshot.inputs.exists()
    assert (
        authorize(project.pk, **selection, token=token, acknowledgements=[], actor=actor, kind="EXCERPT").pk == run.pk
    )
    append_logical_page(logical.pk, expected_number=1, source_page_id=page.source_page_id, orientation=90)
    with pytest.raises(ValidationError):
        authorize(project.pk, **selection, token=token, acknowledgements=[], actor=actor, kind="EXCERPT")
    snapshot, legacy = load_pinned_inputs(run.snapshot.pk)
    assert snapshot.pk == run.snapshot.pk and legacy == []
    assert snapshot.payload["cells"][0]["content"]["inputs"][0]["orientation"] == 0
