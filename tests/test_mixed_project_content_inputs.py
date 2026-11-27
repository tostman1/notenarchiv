"""Shared authorization preserves mixed historical whole-file/region inputs."""

from io import BytesIO

import pytest
from pypdf import PdfReader

from apps.archive.content_geometry_services import append_logical_page
from apps.archive.content_preferences import set_content_preference
from apps.archive.content_services import confirm_content, inspect_content, propose_content
from apps.archive.models import ContentEdition, LogicalPage
from apps.exports.project_content_generation import personal_content_pieces
from apps.exports.snapshot_services import authorize, load_pinned_inputs
from apps.projects.models import PartOverride
from apps.projects.preflight_services import build_report, report_token
from core.pdf import Processor
from tests.test_editions import edition_inputs as legacy_inputs
from tests.test_resolution import resolver_inputs as project_inputs

edition_inputs = legacy_inputs
resolver_inputs = project_inputs


@pytest.mark.django_db
def test_mixed_shared_report_and_generation_use_exact_historical_inputs(resolver_inputs, tmp_path):
    actor, project, arrangement, parts, people, positions, first, _, make = resolver_inputs
    logical = LogicalPage.objects.create()
    page = append_logical_page(logical.pk, expected_number=0, source_page_id=first.source_version.pages.get().pk)
    edition = ContentEdition.objects.create(arrangement=arrangement, part=parts[1])
    revision = propose_content(edition.pk, expected_number=0, inputs=[(page.pk, first.pk), (page.pk, first.pk)])
    inspection = inspect_content(
        revision.pk, actor=actor, expected_fingerprint=revision.fingerprint, visually_reviewed=True
    )
    confirm_content(inspection.pk, actor=actor)
    arrangement.refresh_from_db()
    set_content_preference(arrangement.pk, parts[1].pk, edition.pk, actor=actor, expected_revision=arrangement.revision)
    legacy_file = make(90, part=parts[2])
    assignment = legacy_file.assignments.get()
    PartOverride.objects.create(
        project=project, position=positions[1], participant=people[1], desired_part=parts[2], edition=assignment
    )
    selection = {
        "participant_ids": [people[1].pk],
        "position_ids": [positions[0].pk, positions[1].pk],
        "include_content": True,
    }
    report = build_report(project.pk, **selection)
    assert report.blocking == 0 and report.payload["schema"] == 3
    run = authorize(
        project.pk, **selection, actor=actor, kind="EXCERPT", token=report_token(report, actor), acknowledgements=[]
    )
    assert run.snapshot.project_content_inputs.count() == run.snapshot.inputs.count() == 1
    append_logical_page(logical.pk, expected_number=1, source_page_id=page.source_page_id, orientation=90)
    snapshot, legacy_pins = load_pinned_inputs(run.snapshot.pk)
    assert len(legacy_pins) == 1 and legacy_pins[0].assignment_id == assignment.pk
    scratch = tmp_path / "private-mixed-inputs"
    scratch.mkdir(mode=0o700)
    pieces = personal_content_pieces(snapshot, people[1].pk, Processor(scratch), legacy_pins=legacy_pins)
    assert [(piece["number"], piece["state"]) for piece in pieces] == [(1, "MUSIC"), (2, "MUSIC")]
    assert [len(PdfReader(BytesIO(piece["data"])).pages) for piece in pieces] == [2, 1]
    assert snapshot.payload["cells"][0]["content"]["inputs"][0]["orientation"] == 0
    assert snapshot.payload["cells"][1]["assignment_id"] == str(assignment.pk)
