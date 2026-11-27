"""Explicit page preservation never expands a partial musical approval."""

from io import BytesIO

import pytest
from django.core.exceptions import ValidationError
from pypdf import PdfReader

from apps.exports import content_export_services as services
from apps.exports.content_generation import pieces
from apps.exports.content_policy import plan
from apps.exports.snapshot_services import load_pinned_inputs
from core.pdf import Processor
from tests.test_content_export import confirmed
from tests.test_editions import edition_inputs as legacy_inputs

edition_inputs = legacy_inputs


@pytest.mark.django_db
@pytest.mark.parametrize("policy,count", [("REGIONS", 2), ("PAGES_ONCE", 1), ("PAGES_REPEAT", 2)])
def test_explicit_policy_binds_preview_and_historical_output(edition_inputs, tmp_path, policy, count):
    identity, _, _, _ = confirmed(edition_inputs)
    actor = edition_inputs[0]
    entries = services.report([identity.pk])
    assert sum(item["emit"] for pages in plan(entries, policy) for item in pages) == count
    signed = services.token(entries, actor, policy=policy)
    with pytest.raises(ValidationError):
        services.authorize(
            [identity.pk], signed, actor, policy="PAGES_REPEAT" if policy != "PAGES_REPEAT" else "REGIONS"
        )
    run = services.authorize([identity.pk], signed, actor, policy=policy)
    snapshot, pins = load_pinned_inputs(run.snapshot_id)
    assert len(snapshot.payload["content_editions"][0]["inputs"]) == 2
    scratch = tmp_path / "pdf"
    scratch.mkdir(mode=0o700)
    output = pieces(snapshot, pins, Processor(scratch))
    assert len(PdfReader(BytesIO(output[0]["data"])).pages) == count


@pytest.mark.django_db
def test_partial_confirmation_does_not_allow_whole_page_expansion(edition_inputs):
    identity, _, _, file = confirmed(edition_inputs)
    # Existing file-scoped eligibility is deliberately withdrawn; the explicit
    # content inspection remains historical, but cannot approve other page areas.
    from apps.archive.models import ArchiveFile

    ArchiveFile.objects.filter(pk=file.pk).update(review_state="PENDING")
    entries = services.report([identity.pk])
    signed = services.token(entries, edition_inputs[0], policy="PAGES_ONCE")
    with pytest.raises(ValidationError, match="vollständige"):
        services.authorize([identity.pk], signed, edition_inputs[0], policy="PAGES_ONCE")
