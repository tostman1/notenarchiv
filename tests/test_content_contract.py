"""Whole-file compatibility retains legacy identities, receipts and preferences."""

import pytest
from django.core.exceptions import ValidationError

from apps.archive.content_contract import legacy_content_edition, resolve_legacy_content
from tests.test_editions import choose
from tests.test_editions import edition_inputs as legacy_inputs

edition_inputs = legacy_inputs


def test_legacy_order_and_identity_without_writes(edition_inputs):
    _actor, arrangement, parts, first, _second, _make = edition_inputs
    assignment = first.assignments.get()
    before = (first.revision, first.relative_path, first.publication_operation_id)
    adapted = legacy_content_edition(assignment.pk)
    assert (adapted.edition_id, adapted.legacy_assignment_id) == (assignment.pk, assignment.pk)
    assert (adapted.arrangement_id, adapted.part_id) == (arrangement.pk, parts[0].pk)
    page = first.source_version.pages.get()
    assert len(adapted.inputs) == 1
    item = adapted.inputs[0]
    assert (item.sequence, item.page_index, item.source_page_id) == (0, 0, page.pk)
    assert (item.file_id, item.sha256, item.relative_path) == (first.pk, first.sha256, first.relative_path)
    assert item.logical_page_revision_id is None and item.bounds_points is None
    assert legacy_content_edition(assignment.pk) == adapted
    first.refresh_from_db()
    assert (first.revision, first.relative_path, first.publication_operation_id) == before


def test_unconfirmed_and_corrupt_content_are_unavailable(edition_inputs, settings):
    _actor, _arrangement, _parts, first, _second, make = edition_inputs
    unconfirmed = make(3, confirmed=False)
    with pytest.raises(ValidationError):
        legacy_content_edition(unconfirmed.pk)
    path = settings.CURATED_DIR / first.relative_path
    path.write_bytes(b"synthetic corrupt input")
    with pytest.raises(ValidationError, match="integrity"):
        legacy_content_edition(first.assignments.get().pk)


def test_derivative_does_not_invent_original_page_mapping(edition_inputs):
    *_, make = edition_inputs
    file = make(4, derivative=True)
    adapted = legacy_content_edition(file.assignments.get().pk)
    assert len(adapted.inputs) == 1
    assert adapted.inputs[0].source_page_id is None
    assert adapted.inputs[0].page_index is None
    assert adapted.inputs[0].root_kind == "PROCESSED"


def test_preference_and_explicit_choice_parity(edition_inputs):
    _actor, arrangement, parts, first, second, _make = edition_inputs
    assert resolve_legacy_content(arrangement.pk, parts[0].pk).status == "AMBIGUOUS"
    choose(edition_inputs, second)
    preferred = resolve_legacy_content(arrangement.pk, parts[0].pk)
    assert preferred.origin == "ARCHIVE"
    assert preferred.edition.edition_id == second.assignments.get().pk
    explicit = resolve_legacy_content(arrangement.pk, parts[0].pk, explicit_assignment_id=first.assignments.get().pk)
    assert explicit.origin == "EXPLICIT"
    assert explicit.edition.edition_id == first.assignments.get().pk
    unavailable = resolve_legacy_content(arrangement.pk, parts[0].pk, explicit_assignment_id=arrangement.pk)
    assert unavailable.status == "UNAVAILABLE" and unavailable.edition is None


def test_uniform_resolver_preserves_legacy_choices_and_pins(edition_inputs):
    from apps.archive.content_resolver import resolve_content
    from apps.archive.edition_services import resolve

    _, arrangement, parts, first, second, _ = edition_inputs
    for preference in [None, second, first]:
        choose(edition_inputs, preference)
        for explicit in [None, first.assignments.get().pk, second.assignments.get().pk, arrangement.pk]:
            legacy = resolve(arrangement.pk, parts[0].pk, explicit_assignment_id=explicit)
            uniform = resolve_content(arrangement.pk, parts[0].pk, explicit_edition_id=explicit)
            assert (uniform.status, uniform.origin) == (legacy.status, legacy.origin)
            if legacy.assignment:
                assert uniform.edition.edition_id == legacy.assignment.pk
                assert uniform.edition.inputs[0].sha256 == legacy.assignment.archive_file.sha256
                assert uniform.edition.inputs[0].file_revision == legacy.assignment.archive_file.revision
            else:
                assert uniform.edition is None
