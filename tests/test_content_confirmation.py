"""Explicit partial musical approval cannot confirm an entire source file."""

import pytest
from django.core.exceptions import ValidationError

from apps.archive import models as m
from apps.archive.content_contract import confirmed_content_edition
from apps.archive.content_services import confirm_content, inspect_content, propose_content
from apps.archive.services import ArchiveConflict
from tests.test_editions import edition_inputs as legacy_inputs

edition_inputs = legacy_inputs


def edition(fixture):
    _, arrangement, parts, file, _, _ = fixture
    source = file.source_version.pages.order_by("page_index").first()
    logical = m.LogicalPage.objects.create()
    revision = m.LogicalPageRevision.objects.create(logical_page=logical, number=1, source_page=source)
    identity = m.ContentEdition.objects.create(arrangement=arrangement, part=parts[0])
    return identity, logical, revision, file


@pytest.mark.django_db
def test_exact_order_and_repeated_page_require_explicit_confirmation(edition_inputs):
    identity, _, logical, file = edition(edition_inputs)
    proposal = propose_content(identity.pk, expected_number=0, inputs=[(logical.pk, file.pk), (logical.pk, file.pk)])
    references = list(proposal.references.order_by("sequence"))
    assert [ref.sequence for ref in references] == [0, 1]
    assert references[0].pk != references[1].pk
    with pytest.raises(ValidationError, match="Explicit visual review"):
        inspect_content(
            proposal.pk,
            actor=edition_inputs[0],
            expected_fingerprint=proposal.fingerprint,
            visually_reviewed=False,
        )
    inspection = inspect_content(
        proposal.pk, actor=edition_inputs[0], expected_fingerprint=proposal.fingerprint, visually_reviewed=True
    )
    confirmation = confirm_content(inspection.pk, actor=edition_inputs[0])
    assert confirm_content(inspection.pk, actor=edition_inputs[0]).pk == confirmation.pk
    resolved = confirmed_content_edition(identity.pk)
    assert [item.occurrence_id for item in resolved.inputs] == [ref.pk for ref in references]
    assert all(item.logical_page_revision_id == logical.pk for item in resolved.inputs)
    file.refresh_from_db()
    assert file.review_state == "CONFIRMED"  # Legacy approval was not changed.


@pytest.mark.django_db
def test_new_logical_revision_invalidates_only_new_use(edition_inputs):
    identity, logical, first, file = edition(edition_inputs)
    proposal = propose_content(identity.pk, expected_number=0, inputs=[(first.pk, file.pk)])
    inspection = inspect_content(
        proposal.pk, actor=edition_inputs[0], expected_fingerprint=proposal.fingerprint, visually_reviewed=True
    )
    old = confirm_content(inspection.pk, actor=edition_inputs[0])
    m.LogicalPageRevision.objects.create(logical_page=logical, number=2, source_page=first.source_page, orientation=90)
    with pytest.raises(ArchiveConflict):
        confirm_content(inspection.pk, actor=edition_inputs[0])
    with pytest.raises(ArchiveConflict):
        confirmed_content_edition(identity.pk)
    old.refresh_from_db()
    assert old.inspection_id == inspection.pk


@pytest.mark.django_db
def test_changed_order_requires_new_inspection(edition_inputs):
    identity, _, logical, file = edition(edition_inputs)
    first = propose_content(identity.pk, expected_number=0, inputs=[(logical.pk, file.pk)])
    inspection = inspect_content(
        first.pk, actor=edition_inputs[0], expected_fingerprint=first.fingerprint, visually_reviewed=True
    )
    second = propose_content(identity.pk, expected_number=1, inputs=[(logical.pk, file.pk), (logical.pk, file.pk)])
    assert second.fingerprint != first.fingerprint
    with pytest.raises(ArchiveConflict):
        confirm_content(inspection.pk, actor=edition_inputs[0])
    assert not m.ContentConfirmation.objects.exists()


@pytest.mark.django_db
def test_corrupt_bytes_never_receive_content_inspection(edition_inputs, settings):
    identity, _, logical, file = edition(edition_inputs)
    proposal = propose_content(identity.pk, expected_number=0, inputs=[(logical.pk, file.pk)])
    (settings.CURATED_DIR / file.relative_path).write_bytes(b"synthetic corrupt publication")
    with pytest.raises(ValidationError, match="integrity"):
        inspect_content(
            proposal.pk, actor=edition_inputs[0], expected_fingerprint=proposal.fingerprint, visually_reviewed=True
        )
    assert not m.ContentInspection.objects.exists()


@pytest.mark.django_db
def test_multi_source_partial_approval_preserves_unknown_whole_file(edition_inputs):
    actor, arrangement, parts, _, _, make = edition_inputs
    sources = [make(30, confirmed=False), make(31, confirmed=False)]
    logical = []
    for file in sources:
        logical.append(
            m.LogicalPageRevision.objects.create(
                logical_page=m.LogicalPage.objects.create(),
                number=1,
                source_page=file.source_version.pages.get(page_index=0),
            )
        )
    identity = m.ContentEdition.objects.create(arrangement=arrangement, part=parts[0])
    proposal = propose_content(
        identity.pk,
        expected_number=0,
        inputs=[(logical[1].pk, sources[1].pk), (logical[0].pk, sources[0].pk)],
    )
    inspection = inspect_content(
        proposal.pk, actor=actor, expected_fingerprint=proposal.fingerprint, visually_reviewed=True
    )
    confirm_content(inspection.pk, actor=actor)
    result = confirmed_content_edition(identity.pk)
    assert [item.file_id for item in result.inputs] == [sources[1].pk, sources[0].pk]
    assert [item.source_version_id for item in result.inputs] == [
        sources[1].source_version_id,
        sources[0].source_version_id,
    ]
    for file in sources:
        file.refresh_from_db()
        assert file.review_state != "CONFIRMED"
        assert not file.assignments.exists()


@pytest.mark.django_db
def test_independent_logical_change_does_not_withdraw_other_content(edition_inputs):
    actor = edition_inputs[0]
    first_identity, first_logical, first, file = edition(edition_inputs)
    second_identity, _, second, _ = edition(edition_inputs)
    confirmations = []
    for identity, logical in [(first_identity, first), (second_identity, second)]:
        proposal = propose_content(identity.pk, expected_number=0, inputs=[(logical.pk, file.pk)])
        inspected = inspect_content(
            proposal.pk, actor=actor, expected_fingerprint=proposal.fingerprint, visually_reviewed=True
        )
        confirmations.append(confirm_content(inspected.pk, actor=actor))
    m.LogicalPageRevision.objects.create(
        logical_page=first_logical, number=2, source_page=first.source_page, orientation=180
    )
    with pytest.raises(ArchiveConflict):
        confirmed_content_edition(first_identity.pk)
    assert confirmed_content_edition(second_identity.pk).inputs[0].logical_page_revision_id == second.pk
    assert m.ContentConfirmation.objects.filter(pk__in=[item.pk for item in confirmations]).count() == 2


@pytest.mark.django_db
def test_confirmation_requires_inspecting_active_actor(edition_inputs):
    from django.contrib.auth import get_user_model

    actor = edition_inputs[0]
    other = get_user_model().objects.create_user("synthetic-other-reviewer")
    identity, _, logical, file = edition(edition_inputs)
    proposal = propose_content(identity.pk, expected_number=0, inputs=[(logical.pk, file.pk)])
    inspected = inspect_content(
        proposal.pk, actor=actor, expected_fingerprint=proposal.fingerprint, visually_reviewed=True
    )
    with pytest.raises(ValidationError, match="inspecting reviewer"):
        confirm_content(inspected.pk, actor=other)
    assert not m.ContentConfirmation.objects.exists()
    actor.is_active = False
    actor.save(update_fields=["is_active"])
    with pytest.raises(ValidationError):
        confirm_content(inspected.pk, actor=actor)
    assert not m.ContentConfirmation.objects.exists()
