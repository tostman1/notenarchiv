"""Unreadable content remains blocking despite retained visual confirmation."""

import pytest
from django.core.exceptions import ValidationError

from apps.archive.content_preferences import set_content_preference
from apps.archive.content_services import confirm_content, inspect_content, propose_content
from apps.archive.models import ContentEdition, LogicalPage, LogicalPageRevision
from apps.exports.models import GenerationSnapshot
from apps.exports.snapshot_services import authorize
from apps.projects import preflight_services
from core.pdf import PdfError
from tests.test_editions import edition_inputs as legacy_inputs
from tests.test_resolution import resolver_inputs as project_inputs

edition_inputs = legacy_inputs
resolver_inputs = project_inputs


@pytest.mark.django_db
def test_unreadable_content_blocks_signed_project_authorization(resolver_inputs, monkeypatch):
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
    confirmation = confirm_content(inspection.pk, actor=actor)
    arrangement.refresh_from_db()
    set_content_preference(arrangement.pk, parts[1].pk, edition.pk, actor=actor, expected_revision=arrangement.revision)
    selection = {"participant_ids": [people[1].pk], "position_ids": [positions[0].pk], "include_content": True}

    def unreadable(*args):
        raise PdfError("INVALID_PDF")

    monkeypatch.setattr(preflight_services, "inspect_file", unreadable)
    report = preflight_services.build_report(project.pk, **selection)
    assert report.blocking == 1
    assert report.payload["cells"][0]["content"]["edition_id"] == str(edition.pk)
    assert report.rows[0]["cells"][0]["inspection"]["error"] == "UNREADABLE_PDF"
    with pytest.raises(ValidationError):
        authorize(
            project.pk,
            **selection,
            token=preflight_services.report_token(report, actor),
            acknowledgements=[],
            actor=actor,
            kind="EXCERPT",
        )
    assert not GenerationSnapshot.objects.exists()
    assert confirmation.__class__.objects.filter(pk=confirmation.pk).exists()
