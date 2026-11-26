from uuid import uuid4

import pytest

from apps.archive.content_resolver import resolve_content
from apps.archive.content_services import confirm_content, inspect_content, propose_content
from tests.test_content_confirmation import edition
from tests.test_editions import edition_inputs as legacy_inputs

edition_inputs = legacy_inputs
pytestmark = pytest.mark.django_db


def test_uniform_explicit_content_selection_and_no_manual_fallback(edition_inputs):
    actor, arrangement, parts, first, _, _ = edition_inputs
    content, _, logical, _ = edition(edition_inputs)
    proposal = propose_content(content.pk, expected_number=0, inputs=[(str(logical.pk), str(first.pk))])
    before = resolve_content(arrangement.pk, parts[0].pk, explicit_edition_id=content.pk)
    assert before.status == "UNAVAILABLE"
    inspection = inspect_content(
        proposal.pk, actor=actor, expected_fingerprint=proposal.fingerprint, visually_reviewed=True
    )
    confirm_content(inspection.pk, actor=actor)
    result = resolve_content(arrangement.pk, parts[0].pk, explicit_edition_id=content.pk)
    assert result.status == "AVAILABLE"
    assert result.origin == "EXPLICIT"
    assert result.edition.edition_id == content.pk
    assert result.edition.inputs[0].logical_page_revision_id == logical.pk
    assert resolve_content(arrangement.pk, parts[0].pk, explicit_edition_id=uuid4()).status == "UNAVAILABLE"
    assert resolve_content(arrangement.pk, parts[0].pk).status == "AMBIGUOUS"
