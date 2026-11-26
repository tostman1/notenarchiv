import pytest
from django.core.exceptions import ValidationError

from apps.archive.content_preferences import set_content_preference
from apps.archive.content_resolver import resolve_content
from apps.archive.content_services import confirm_content, inspect_content, propose_content
from apps.archive.edition_services import resolve, set_preference
from apps.archive.models import LogicalPageRevision
from apps.archive.services import ArchiveConflict
from tests.test_content_confirmation import edition
from tests.test_editions import edition_inputs as legacy_inputs

edition_inputs = legacy_inputs
pytestmark = pytest.mark.django_db


def test_content_preference_history_explicit_priority_and_no_legacy_fallback(edition_inputs):
    actor, arrangement, parts, first, second, _ = edition_inputs
    identity, logical, page, file = edition(edition_inputs)
    revision = propose_content(identity.pk, expected_number=0, inputs=[(page.pk, file.pk)])
    inspection = inspect_content(
        revision.pk, actor=actor, expected_fingerprint=revision.fingerprint, visually_reviewed=True
    )
    confirm_content(inspection.pk, actor=actor)
    arrangement.refresh_from_db()
    preference = set_content_preference(
        arrangement.pk, parts[0].pk, identity.pk, actor=actor, expected_revision=arrangement.revision
    )
    assert preference.assignment_id is None
    assert preference.changes.get().selected_content_id == identity.pk
    result = resolve_content(arrangement.pk, parts[0].pk)
    assert (result.status, result.origin, result.edition.edition_id) == ("AVAILABLE", "ARCHIVE", identity.pk)
    manual = first.assignments.get(part=parts[0])
    explicit = resolve_content(arrangement.pk, parts[0].pk, explicit_edition_id=manual.pk)
    assert explicit.edition.edition_id == manual.pk
    # Until the project contract consumes content, old readers fail closed rather than substitute.
    assert (resolve(arrangement.pk, parts[0].pk).status, resolve(arrangement.pk, parts[0].pk).origin) == (
        "UNAVAILABLE",
        "ARCHIVE",
    )
    LogicalPageRevision.objects.create(logical_page=logical, number=2, source_page=page.source_page, orientation=90)
    assert resolve_content(arrangement.pk, parts[0].pk).status == "UNAVAILABLE"
    arrangement.refresh_from_db()
    set_preference(arrangement.pk, parts[0].pk, manual.pk, actor=actor, expected_revision=arrangement.revision)
    preference.refresh_from_db()
    assert preference.content_edition_id is None
    assert preference.changes.order_by("created_at", "id").last().previous_content_id == identity.pk
    assert resolve_content(arrangement.pk, parts[0].pk).edition.edition_id == manual.pk


def test_content_preference_rejects_wrong_scope_unconfirmed_and_stale_revision(edition_inputs):
    actor, arrangement, parts, _, _, _ = edition_inputs
    identity, _, page, file = edition(edition_inputs)
    arrangement.refresh_from_db()
    with pytest.raises(ValidationError):
        set_content_preference(
            arrangement.pk, parts[0].pk, identity.pk, actor=actor, expected_revision=arrangement.revision
        )
    revision = propose_content(identity.pk, expected_number=0, inputs=[(page.pk, file.pk)])
    inspection = inspect_content(
        revision.pk, actor=actor, expected_fingerprint=revision.fingerprint, visually_reviewed=True
    )
    confirm_content(inspection.pk, actor=actor)
    with pytest.raises(ValidationError, match="exact arrangement"):
        set_content_preference(
            arrangement.pk, parts[1].pk, identity.pk, actor=actor, expected_revision=arrangement.revision
        )
    with pytest.raises(ArchiveConflict):
        set_content_preference(arrangement.pk, parts[0].pk, identity.pk, actor=actor, expected_revision=False)
