"""Synthetic mass and movements retain independent editions and shared pages."""

from io import BytesIO

import pytest
from pypdf import PdfReader

from apps.archive import models as m
from apps.archive.content_contract import confirmed_content_edition
from apps.archive.content_rendering import render_content
from apps.archive.content_services import confirm_content, inspect_content, propose_content
from apps.catalog.collection_services import add_relationship
from apps.catalog.models import Arrangement, Work
from apps.exports.content_inputs import capture_content, load_content
from core.pdf import Processor
from tests.test_editions import edition_inputs as legacy_inputs

edition_inputs = legacy_inputs


@pytest.mark.django_db
def test_mass_and_movements_share_explicit_pages_without_merging_editions(edition_inputs, tmp_path):
    actor, _, parts, *_rest, make = edition_inputs
    parent = Work.objects.create(title="Synthetic Deutsche Messe")
    movements = [Work.objects.create(title="Repeated synthetic movement") for _ in range(3)]
    parent_arrangement = Arrangement.objects.create(work=parent)
    arrangements = [Arrangement.objects.create(work=work) for work in movements]
    for position, work in enumerate(movements):
        add_relationship(parent.pk, work.pk, kind="MOVEMENT", position=position)
    files = [make(70 + index, confirmed=False) for index in range(2)]
    logicals = [
        m.LogicalPageRevision.objects.create(
            logical_page=m.LogicalPage.objects.create(), number=1, source_page=file.source_version.pages.get()
        )
        for file in files
    ]
    # A shared continuation is an explicit occurrence, not an inferred duplicate.
    movement_inputs = [
        [(logicals[0].pk, files[0].pk)],
        [(logicals[0].pk, files[0].pk), (logicals[1].pk, files[1].pk)],
        [(logicals[1].pk, files[1].pk)],
    ]

    def reviewed(arrangement, inputs):
        edition = m.ContentEdition.objects.create(arrangement=arrangement, part=parts[0])
        proposal = propose_content(edition.pk, expected_number=0, inputs=inputs)
        inspection = inspect_content(
            proposal.pk, actor=actor, expected_fingerprint=proposal.fingerprint, visually_reviewed=True
        )
        confirm_content(inspection.pk, actor=actor)
        return edition

    editions = [
        reviewed(arrangement, inputs) for arrangement, inputs in zip(arrangements, movement_inputs, strict=True)
    ]
    complete = reviewed(parent_arrangement, [item for inputs in movement_inputs for item in inputs])
    resolved = confirmed_content_edition(complete.pk)
    assert [item.source_version_id for item in resolved.inputs] == [
        files[0].source_version_id,
        files[0].source_version_id,
        files[1].source_version_id,
        files[1].source_version_id,
    ]
    assert len({item.occurrence_id for item in resolved.inputs}) == 4
    assert len({edition.pk for edition in editions + [complete]}) == 4
    captured = capture_content(complete.pk)
    scratch = tmp_path / "private-mass-rendering"
    scratch.mkdir(mode=0o700)
    for edition, page_count in zip(editions + [complete], [1, 2, 1, 4], strict=True):
        assert len(PdfReader(BytesIO(render_content(edition.pk, processor=Processor(scratch)))).pages) == page_count
    assert load_content(captured) == resolved
    assert parent.component_relationships.count() == 3
    assert len({work.pk for work in movements}) == 3
    assert all(file.review_state != "CONFIRMED" and not file.assignments.exists() for file in files)
