"""Ordered project adaptation preserves exact legacy resolver decisions."""

import pytest

from apps.archive import edition_services
from apps.projects.resolution_services import ResolutionSession
from tests.test_editions import edition_inputs as legacy_inputs
from tests.test_resolution import resolver_inputs as project_inputs

edition_inputs = legacy_inputs
resolver_inputs = project_inputs


@pytest.mark.django_db
def test_ordered_project_adapter_preserves_preference_and_all_pins(resolver_inputs):
    actor, project, arrangement, parts, people, positions, first, second, _ = resolver_inputs
    for file in (first, second):
        arrangement.refresh_from_db()
        assignment = file.assignments.get()
        edition_services.set_preference(
            arrangement.pk,
            parts[1].pk,
            assignment.pk,
            actor=actor,
            expected_revision=arrangement.revision,
        )
        session = ResolutionSession(project.pk)
        expected = session.verified_resolution(positions[0].pk, people[1].pk)
        result, edition = session.ordered_inputs(positions[0].pk, people[1].pk)
        assert result == expected
        assert edition.edition_id == assignment.pk
        assert [entry.sequence for entry in edition.inputs] == [0]
        assert all(entry.file_id == file.pk and entry.sha256 == file.sha256 for entry in edition.inputs)
        assert all(entry.logical_page_revision_id is None and entry.bounds_points is None for entry in edition.inputs)
    project.refresh_from_db()
    assert project.revision == 1 and project.history.count() == 1


@pytest.mark.django_db
def test_ordered_project_adapter_does_not_invent_missing_or_ambiguous_music(resolver_inputs):
    _, project, _, _, people, positions, *_ = resolver_inputs
    session = ResolutionSession(project.pk)
    for person, position, expected in ((1, 0, "AMBIGUOUS"), (0, 0, "MISSING"), (1, 2, "RESERVE")):
        result, edition = session.ordered_inputs(positions[position].pk, people[person].pk)
        assert result.status == expected and edition is None
