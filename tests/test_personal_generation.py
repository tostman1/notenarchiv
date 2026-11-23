"""Pinned personal folder composition and no partial download exposure."""

from io import BytesIO

import pytest
from pypdf import PdfReader

from apps.exports.generation import personal_pieces
from apps.exports.snapshot_services import authorize, load_pinned_inputs
from apps.projects.models import ProjectParticipant, ProjectPosition
from apps.projects.preflight_services import build_report, report_token
from core.pdf import Processor
from tests.test_generation_snapshots import permission
from tests.test_resolution import resolver_inputs as _resolution_fixture

resolver_inputs = _resolution_fixture


def test_personal_folder_builds_from_pins_after_project_edit(resolver_inputs, tmp_path):
    run = authorize(**permission(resolver_inputs))
    snapshot, pins = load_pinned_inputs(run.snapshot_id)
    person = snapshot.participants.get()
    ProjectParticipant.objects.filter(pk=person.participant_id).update(display_name="Changed synthetic")
    ProjectPosition.objects.filter(pk=resolver_inputs[5][0].pk).update(arrangement=None)
    pieces = personal_pieces(snapshot, pins, person.participant_id)
    assert [p["number"] for p in pieces] == [1, 2, 3]
    assert [p["state"] for p in pieces] == ["MUSIC", "MUSIC", "RESERVE"]
    data = Processor(tmp_path).compose(pieces, project="Synthetic", participant=person.display_name)
    assert len(PdfReader(BytesIO(data)).pages) == 3


def test_missing_person_has_placeholder_at_each_shared_position(resolver_inputs, tmp_path):
    run = authorize(**permission(resolver_inputs, missing=True))
    snapshot, pins = load_pinned_inputs(run.snapshot_id)
    pieces = personal_pieces(snapshot, pins, snapshot.participants.get().participant_id)
    data = Processor(tmp_path).compose(pieces, project="Synthetic")
    reader = PdfReader(BytesIO(data))
    assert len(reader.pages) == 3
    assert all("Noten fehlen" in page.extract_text() for page in reader.pages[1:])


def test_multi_person_exact_parts_and_editions_share_contents(resolver_inputs, tmp_path):
    actor, project, arr, parts, people, positions, first, second, make = resolver_inputs
    from apps.projects.models import PartOverride

    third = make(3, part=parts[2])
    for person, part, file in (
        (people[0], parts[1], first),
        (people[1], parts[1], second),
        (people[2], parts[2], third),
    ):
        for position in positions[:2]:
            PartOverride.objects.create(
                project=project,
                participant=person,
                position=position,
                desired_part=part,
                edition=file.assignments.get(),
            )
    report = build_report(project.pk)
    run = authorize(
        project.pk,
        participant_ids=list(report.session.participants),
        position_ids=list(report.session.positions),
        token=report_token(report, actor),
        acknowledgements=[],
        actor=actor,
    )
    snapshot, pins = load_pinned_inputs(run.snapshot_id)
    contents = []
    for person in people:
        pieces = personal_pieces(snapshot, pins, person.pk)
        reader = PdfReader(BytesIO(Processor(tmp_path).compose(pieces, project="Synthetisch")))
        contents.append(reader.pages[0].extract_text())
        source = PdfReader(BytesIO(pieces[0]["data"]))
        assert reader.pages[1].mediabox == source.pages[0].mediabox
        assert reader.pages[1].get_contents().get_data() == source.pages[0].get_contents().get_data()
    assert len(set(contents)) == 1 and "Reserve" in contents[0]
    assert {pin.archive_file_id for pin in pins} == {first.pk, second.pk, third.pk}


def test_personal_input_budget_is_checked_before_accumulating_bytes(resolver_inputs, settings):
    run = authorize(**permission(resolver_inputs))
    snapshot, pins = load_pinned_inputs(run.snapshot_id)
    settings.PDF_MAX_BYTES = 1
    from django.core.exceptions import ValidationError

    with pytest.raises(ValidationError, match="limit"):
        personal_pieces(snapshot, pins, snapshot.participants.get().participant_id)
