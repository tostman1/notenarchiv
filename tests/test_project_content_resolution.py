"""Versioned content selection reuses the shared project rules without legacy changes."""

import pytest

from apps.archive.content_geometry_services import append_logical_page
from apps.archive.content_preferences import set_content_preference
from apps.archive.content_services import confirm_content, inspect_content, propose_content
from apps.archive.models import ContentEdition, LogicalPage, LogicalPageRevision
from apps.projects.models import PartOverride
from apps.projects.resolution_services import ContentProjectResolution, ResolutionSession
from tests.test_editions import edition_inputs as legacy_inputs
from tests.test_resolution import resolver_inputs as project_inputs

edition_inputs = legacy_inputs
resolver_inputs = project_inputs


@pytest.mark.django_db
def test_versioned_shared_session_selects_exact_content_and_never_falls_back(resolver_inputs):
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
    assert ResolutionSession(project.pk).resolve(positions[0].pk, people[1].pk).status == "INVALID"
    session = ResolutionSession(project.pk, include_content=True)
    result, ordered = session.ordered_inputs(positions[0].pk, people[1].pk)
    assert isinstance(result, ContentProjectResolution)
    assert result.status == "AVAILABLE" and result.edition_origin == "ARCHIVE"
    assert result.content_edition_id == edition.pk and result.assignment_id is None
    assert ordered.edition_id == edition.pk and ordered.inputs[0].logical_page_revision_id == page.pk
    override = PartOverride.objects.create(
        project=project,
        position=positions[0],
        participant=people[1],
        desired_part=parts[1],
        edition_id=first.assignments.get().pk,
    )
    explicit, legacy = ResolutionSession(project.pk, include_content=True).ordered_inputs(positions[0].pk, people[1].pk)
    assert explicit.edition_origin == "PERSONAL" and getattr(explicit, "content_edition_id", None) is None
    assert legacy.legacy_assignment_id == first.assignments.get().pk
    PartOverride.objects.filter(pk=override.pk).update(active=False)
    append_logical_page(logical.pk, expected_number=1, source_page_id=page.source_page_id, orientation=90)
    assert session.verified_resolution(positions[0].pk, people[1].pk).status == "INVALID"
    assert (
        ResolutionSession(project.pk, include_content=True).resolve(positions[0].pk, people[1].pk).status == "INVALID"
    )
    assert project.revision == 1
