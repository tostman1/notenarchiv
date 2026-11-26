"""Current confirmed content reaches only verified isolated derivative inputs."""

import io

import pytest
from pypdf import PdfReader

from apps.archive import models as m
from apps.archive.content_rendering import render_content
from apps.archive.content_services import confirm_content, inspect_content, propose_content
from apps.archive.services import ArchiveConflict
from core.pdf import Processor
from tests.test_content_confirmation import edition
from tests.test_editions import edition_inputs as legacy_inputs

edition_inputs = legacy_inputs


@pytest.mark.django_db
def test_confirmed_repeated_content_render_preserves_source_and_history(edition_inputs, tmp_path):
    identity, logical, revision, file = edition(edition_inputs)
    proposal = propose_content(identity.pk, expected_number=0, inputs=[(revision.pk, file.pk)] * 2)
    inspection = inspect_content(
        proposal.pk, actor=edition_inputs[0], expected_fingerprint=proposal.fingerprint, visually_reviewed=True
    )
    confirmation = confirm_content(inspection.pk, actor=edition_inputs[0])
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    worker = Processor(scratch)
    result = PdfReader(io.BytesIO(render_content(identity.pk, processor=worker)))
    assert len(result.pages) == 2
    expected = tuple(revision.content_bounds_points)
    assert all(
        tuple(page.mediabox) == (0, 0, expected[2] - expected[0], expected[3] - expected[1]) for page in result.pages
    )
    assert m.ContentConfirmation.objects.get(pk=confirmation.pk).inspection_id == inspection.pk
    file.refresh_from_db()
    assert file.revision == proposal.references.first().file_revision
    m.LogicalPageRevision.objects.create(logical_page=logical, number=2, source_page=revision.source_page)
    with pytest.raises(ArchiveConflict):
        render_content(identity.pk, processor=worker)


@pytest.mark.django_db
def test_legacy_render_uses_whole_document_without_invented_regions(edition_inputs, tmp_path):
    file = edition_inputs[3]
    assignment = file.assignments.first()
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    assert (
        len(PdfReader(io.BytesIO(render_content(assignment.pk, legacy=True, processor=Processor(scratch)))).pages) == 1
    )


@pytest.mark.django_db
def test_revision_change_during_render_cannot_return_derivative(edition_inputs):
    identity, logical, revision, file = edition(edition_inputs)
    proposal = propose_content(identity.pk, expected_number=0, inputs=[(revision.pk, file.pk)])
    inspection = inspect_content(
        proposal.pk, actor=edition_inputs[0], expected_fingerprint=proposal.fingerprint, visually_reviewed=True
    )
    confirm_content(inspection.pk, actor=edition_inputs[0])

    class ChangingProcessor:
        def logical_pages(self, inputs, selections):
            m.LogicalPageRevision.objects.create(logical_page=logical, number=2, source_page=revision.source_page)
            return b"not returned"

    with pytest.raises(ArchiveConflict):
        render_content(identity.pk, processor=ChangingProcessor())
