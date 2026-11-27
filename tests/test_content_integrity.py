import io

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.archive.content_integrity import report
from apps.archive.content_services import confirm_content, inspect_content, propose_content
from tests.test_content_confirmation import edition
from tests.test_editions import edition_inputs as legacy_inputs

edition_inputs = legacy_inputs
pytestmark = pytest.mark.django_db


def test_report_keeps_stale_history_and_emits_no_private_values(edition_inputs):
    actor = edition_inputs[0]
    identity, logical, page, file = edition(edition_inputs)
    revision = propose_content(identity.pk, expected_number=0, inputs=[(page.pk, file.pk)])
    inspection = inspect_content(
        revision.pk, actor=actor, expected_fingerprint=revision.fingerprint, visually_reviewed=True
    )
    confirm_content(inspection.pk, actor=actor)
    from apps.archive.content_geometry_services import append_logical_page

    append_logical_page(logical.pk, expected_number=1, source_page_id=page.source_page_id, orientation=90)
    result = report()
    assert result["ok"] and result["counts"]["contenteditionrevision"] == 1
    output = io.StringIO()
    call_command("check_content_integrity", stdout=output)
    assert str(file.pk) not in output.getvalue() and file.relative_path not in output.getvalue()
    assert identity.revisions.count() == 1 and inspection.confirmation.pk


def test_incomplete_source_mapping_is_reported_not_repaired(edition_inputs):
    file = edition_inputs[3]
    # Missing historical mapping simulates an interrupted additive backfill.
    file.source_version.pages.all().delete()
    result = report()
    assert not result["ok"] and "SOURCE_PAGE_MAPPING" in result["failures"]
    with pytest.raises(CommandError):
        call_command("check_content_integrity", stdout=io.StringIO())
    assert file.source_version.pages.count() == 0
