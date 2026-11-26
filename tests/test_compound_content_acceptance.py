"""Synthetic booklet identities remain independent of source order and instrument."""

import pytest
from django.core.exceptions import ValidationError

from apps.archive.content_contract import confirmed_content_edition
from apps.archive.content_models import ContentEdition, LogicalPage, LogicalPageRevision
from apps.archive.content_services import confirm_content, inspect_content, propose_content
from apps.catalog.collection_services import add_membership
from apps.catalog.models import Arrangement, Collection, Work
from apps.exports.content_inputs import capture_content, load_content
from tests.test_editions import edition_inputs as legacy_inputs

edition_inputs = legacy_inputs


@pytest.mark.django_db
def test_incremental_booklet_uses_shared_pages_without_merging_work_identity(edition_inputs):
    actor, _arrangement, parts, *_rest, make = edition_inputs
    collection = Collection.objects.create(title="Synthetic 125-piece booklet", metadata={"publisher": "Synthetic"})
    arrangements = []
    for position in range(125):
        work = Work.objects.create(title="Repeated synthetic title")
        add_membership(collection.pk, work.pk, position=position, original_song_number=str(position + 1))
        arrangements.append(Arrangement.objects.create(work=work))
    files = [make(40 + index, confirmed=False) for index in range(2)]
    pages = [
        LogicalPageRevision.objects.create(
            logical_page=LogicalPage.objects.create(),
            number=1,
            source_page=file.source_version.pages.get(),
            orientation=index * 90,
        )
        for index, file in enumerate(files)
    ]
    editions = []
    for work_index in range(3):
        for instrument_index, part in enumerate(parts):
            identity = ContentEdition.objects.create(arrangement=arrangements[work_index], part=part)
            # Distinct musical identities explicitly reuse pages. Continuation
            # counts and orientation differ between instrumental booklets.
            proposal = propose_content(
                identity.pk,
                expected_number=0,
                inputs=[(pages[instrument_index].pk, files[instrument_index].pk)] * (1 + instrument_index),
            )
            inspection = inspect_content(
                proposal.pk, actor=actor, expected_fingerprint=proposal.fingerprint, visually_reviewed=True
            )
            confirm_content(inspection.pk, actor=actor)
            editions.append(identity)
    unknown = ContentEdition.objects.create(arrangement=arrangements[3], part=parts[0])
    with pytest.raises(ValidationError):
        confirmed_content_edition(unknown.pk)
    assert collection.memberships.count() == 125
    assert len({row.work_id for row in collection.memberships.all()}) == 125
    for index, identity in enumerate(editions):
        resolved = confirmed_content_edition(identity.pk)
        instrument_index = index % 2
        assert len(resolved.inputs) == 1 + instrument_index
        assert {entry.file_id for entry in resolved.inputs} == {files[instrument_index].pk}
        assert {entry.orientation for entry in resolved.inputs} == {instrument_index * 90}
        assert len({entry.occurrence_id for entry in resolved.inputs}) == len(resolved.inputs)
        assert load_content(capture_content(identity.pk)) == resolved
    for file in files:
        file.refresh_from_db()
        assert file.review_state != "CONFIRMED"
        assert not file.assignments.exists()
