"""Authorized content export preserves old inputs without approving a whole file."""

from io import BytesIO

import pytest
from django.core.exceptions import ValidationError
from pypdf import PdfReader

from apps.archive.content_geometry_services import append_logical_page
from apps.archive.content_services import confirm_content, inspect_content, propose_content
from apps.archive.services import ArchiveConflict
from apps.exports import content_export_services as services
from apps.exports.content_generation import pieces
from apps.exports.snapshot_services import load_pinned_inputs
from core.pdf import Processor
from tests.test_content_confirmation import edition
from tests.test_editions import edition_inputs as legacy_inputs

edition_inputs = legacy_inputs


def confirmed(inputs):
    identity, logical_identity, logical, file = edition(inputs)
    actor = inputs[0]
    proposal = propose_content(identity.pk, expected_number=0, inputs=[(logical.pk, file.pk), (logical.pk, file.pk)])
    inspection = inspect_content(
        proposal.pk, actor=actor, expected_fingerprint=proposal.fingerprint, visually_reviewed=True
    )
    confirm_content(inspection.pk, actor=actor)
    return identity, logical_identity, logical, file


@pytest.mark.django_db
def test_authorized_content_keeps_historical_sequence_after_edit(edition_inputs, tmp_path):
    identity, logical_identity, logical, file = confirmed(edition_inputs)
    actor = edition_inputs[0]
    entries = services.report([identity.pk])
    authorization = services.token(entries, actor)
    run = services.authorize([identity.pk], authorization, actor)
    assert services.authorize([identity.pk], authorization, actor).pk == run.pk
    assert run.snapshot.inputs.count() == 0
    assert run.snapshot.content_inputs.count() == 1
    append_logical_page(logical_identity.pk, expected_number=1, source_page_id=logical.source_page_id, orientation=90)
    with pytest.raises(ArchiveConflict):
        services.report([identity.pk])
    snapshot, pins = load_pinned_inputs(run.snapshot_id)
    scratch = tmp_path / "pdf"
    scratch.mkdir(mode=0o700)
    result = pieces(snapshot, pins, Processor(scratch))
    assert len(result) == 1
    assert len(PdfReader(BytesIO(result[0]["data"])).pages) == 2
    assert snapshot.payload["content_editions"][0]["inputs"][0]["orientation"] == 0
    assert snapshot.payload["content_editions"][0]["inputs"][0]["file_id"] == str(file.pk)


@pytest.mark.django_db
def test_content_authorization_binds_actor_variant_and_selection(edition_inputs):
    identity, _, _, _ = confirmed(edition_inputs)
    actor = edition_inputs[0]
    authorization = services.token(services.report([identity.pk]), actor)
    with pytest.raises(ValidationError):
        services.authorize([identity.pk], authorization, actor, variant="PRINT")
    with pytest.raises(ValidationError):
        services.authorize([identity.pk], authorization + "tampered", actor)
    with pytest.raises(ValidationError):
        services.report([identity.pk, identity.pk])
    actor.is_active = False
    actor.save(update_fields=["is_active"])
    with pytest.raises(ValidationError):
        services.authorize([identity.pk], authorization, actor)


@pytest.mark.django_db
def test_content_authorization_rechecks_title_under_lock(edition_inputs, monkeypatch):
    identity, _, _, _ = confirmed(edition_inputs)
    actor = edition_inputs[0]
    authorization = services.token(services.report([identity.pk]), actor)
    original = services.report

    def changed_report(identifiers):
        entries = original(identifiers)
        work = identity.arrangement.work
        work.title = "Changed synthetic title"
        work.save()
        return entries

    monkeypatch.setattr(services, "report", changed_report)
    with pytest.raises(ValidationError, match="während"):
        services.authorize([identity.pk], authorization, actor)


def test_content_selection_consumes_only_bounded_identifiers():
    consumed = []

    def identifiers():
        for number in range(10000):
            consumed.append(number)
            yield number

    with pytest.raises(ValidationError):
        services.report(identifiers())
    assert len(consumed) == 101
