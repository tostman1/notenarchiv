"""Inspection previews use persisted proposal order, not mutable UI selection."""

import pytest
from django.http import Http404

from apps.archive import models as m
from apps.archive.content_geometry_services import append_region
from apps.archive.content_preview_services import proposal_preview
from tests.test_region_preview import region_preview  # noqa: F401
from tests.test_region_sequence_services import propose


@pytest.mark.django_db
def test_proposal_preview_pins_occurrences_and_history(region_preview, monkeypatch):  # noqa: F811
    file, regions, _ = region_preview
    revision = propose(file, [regions[1], regions[1]])
    append_region(regions[1].region_id, expected_number=2, bounds_points=[100, 0, 180, 180])
    captured = []

    def render(publication, identifiers):
        captured.extend(identifiers)
        assert publication.pk == file.pk
        return b"synthetic-preview"

    monkeypatch.setattr("apps.archive.content_preview_services.region_sequence", render)
    assert proposal_preview(file, revision.pk) == b"synthetic-preview"
    assert captured == [regions[1].pk, regions[1].pk]
    assert m.ContentInspection.objects.count() == m.ContentConfirmation.objects.count() == 0


@pytest.mark.django_db
def test_proposal_preview_rejects_wrong_publication_pin(region_preview):  # noqa: F811
    file, regions, _ = region_preview
    revision = propose(file, [regions[1]])
    file.revision += 1
    with pytest.raises(Http404):
        proposal_preview(file, revision.pk)
