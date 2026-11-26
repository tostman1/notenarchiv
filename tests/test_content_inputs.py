"""Historical content pins survive new-use invalidation without selecting replacements."""

from copy import deepcopy

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction

from apps.archive.content_geometry_services import append_logical_page
from apps.archive.content_services import confirm_content, inspect_content, propose_content
from apps.archive.services import ArchiveConflict
from apps.exports.content_inputs import capture_content, load_content
from apps.exports.models import GenerationSnapshot, SnapshotContentInput
from apps.projects.preflight_services import fingerprint
from tests.test_content_confirmation import edition
from tests.test_editions import edition_inputs as legacy_inputs

edition_inputs = legacy_inputs


@pytest.mark.django_db
def test_historical_inputs_remain_exact_after_new_logical_revision(edition_inputs):
    identity, logical_identity, logical, file = edition(edition_inputs)
    actor = edition_inputs[0]
    proposal = propose_content(identity.pk, expected_number=0, inputs=[(logical.pk, file.pk), (logical.pk, file.pk)])
    inspection = inspect_content(
        proposal.pk, actor=actor, expected_fingerprint=proposal.fingerprint, visually_reviewed=True
    )
    confirm_content(inspection.pk, actor=actor)
    payload = capture_content(identity.pk)
    original = deepcopy(payload)
    resolved = load_content(payload)
    assert len(resolved.inputs) == 2
    assert resolved.inputs[0].occurrence_id != resolved.inputs[1].occurrence_id
    append_logical_page(logical_identity.pk, expected_number=1, source_page_id=logical.source_page_id, orientation=90)
    with pytest.raises(ArchiveConflict):
        capture_content(identity.pk)
    assert load_content(payload) == resolved
    assert payload == original


@pytest.mark.django_db
def test_historical_inputs_reject_tampering(edition_inputs):
    identity, _, logical, file = edition(edition_inputs)
    actor = edition_inputs[0]
    proposal = propose_content(identity.pk, expected_number=0, inputs=[(logical.pk, file.pk)])
    inspection = inspect_content(
        proposal.pk, actor=actor, expected_fingerprint=proposal.fingerprint, visually_reviewed=True
    )
    confirm_content(inspection.pk, actor=actor)
    payload = capture_content(identity.pk)
    for key, value in [("orientation", 90), ("sha256", "0" * 64), ("sequence", 1)]:
        changed = deepcopy(payload)
        changed["inputs"][0][key] = value
        with pytest.raises(ValidationError, match="input mismatch"):
            load_content(changed)
    payload["schema"] = "unknown"
    with pytest.raises(ValidationError, match="schema"):
        load_content(payload)


@pytest.mark.django_db
def test_snapshot_content_pin_protects_exact_file_and_confirmation(edition_inputs):
    identity, _, logical, file = edition(edition_inputs)
    actor = edition_inputs[0]
    proposal = propose_content(identity.pk, expected_number=0, inputs=[(logical.pk, file.pk)])
    inspection = inspect_content(
        proposal.pk, actor=actor, expected_fingerprint=proposal.fingerprint, visually_reviewed=True
    )
    approval = confirm_content(inspection.pk, actor=actor)
    content = capture_content(identity.pk)
    payload = {"schema": 2, "project": "None", "revision": 0, "blocking": 0, "content_editions": [content]}
    snapshot = GenerationSnapshot.objects.create(
        project_revision=0,
        kind="ARCHIVE_NOTES",
        payload=payload,
        sha256=fingerprint(payload),
        preflight_sha256=fingerprint(payload),
        actor=actor,
    )
    pin = SnapshotContentInput.objects.create(snapshot=snapshot, ordinal=0, confirmation=approval, payload=content)
    assert load_content(pin.payload).inputs[0].file_id == file.pk
    with pytest.raises(IntegrityError, match="pinned generation content input"), transaction.atomic():
        file.__class__.objects.filter(pk=file.pk).update(relative_path="changed.pdf")
    with (
        pytest.raises(IntegrityError, match="immutable generation history"),
        transaction.atomic(),
        connection.cursor() as cursor,
    ):
        cursor.execute("UPDATE exports_snapshotcontentinput SET ordinal=1 WHERE id=%s", [pin.pk.hex])
    with pytest.raises(ValidationError, match="authorization payload"):
        SnapshotContentInput.objects.create(snapshot=snapshot, ordinal=1, confirmation=approval, payload=content)
