"""Pinned personal folder composition and no partial download exposure."""

from io import BytesIO

from pypdf import PdfReader

from apps.exports.generation import personal_pieces
from apps.exports.snapshot_services import authorize, load_pinned_inputs
from core.pdf import Processor
from tests.test_generation_snapshots import permission
from tests.test_resolution import resolver_inputs as _resolution_fixture

resolver_inputs = _resolution_fixture


def test_personal_folder_builds_from_pins_after_project_edit(resolver_inputs, tmp_path):
    run = authorize(**permission(resolver_inputs))
    snapshot, pins = load_pinned_inputs(run.snapshot_id)
    person = snapshot.participants.get()
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
