import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.archive import models as archive
from apps.archive.content_geometry_services import append_logical_page
from apps.archive.content_services import confirm_content, inspect_content, propose_content
from apps.exports.content_inputs import capture_content
from apps.exports.models import GenerationSnapshot, SnapshotProjectContentInput
from apps.exports.project_content_inputs import load_project_content_pins
from apps.projects.preflight_services import fingerprint
from tests.test_editions import edition_inputs as legacy_inputs
from tests.test_resolution import resolver_inputs as resolution_inputs

edition_inputs = legacy_inputs
resolver_inputs = resolution_inputs


@pytest.mark.django_db
def test_historical_project_content_cell_is_protected(resolver_inputs):
    actor, project, arrangement, parts, people, positions, file, *_ = resolver_inputs
    page = file.source_version.pages.first()
    logical = archive.LogicalPage.objects.create()
    revision = append_logical_page(logical.pk, expected_number=0, source_page_id=page.pk)
    edition = archive.ContentEdition.objects.create(arrangement=arrangement, part=parts[1])
    proposal = propose_content(edition.pk, expected_number=0, inputs=[(revision.pk, file.pk)])
    inspection = inspect_content(
        proposal.pk, actor=actor, expected_fingerprint=proposal.fingerprint, visually_reviewed=True
    )
    confirm_content(inspection.pk, actor=actor)
    content = capture_content(edition.pk)
    payload = {
        "schema": 3,
        "project": str(project.pk),
        "revision": project.revision,
        "blocking": 0,
        "positions": [{"id": str(positions[0].pk), "arrangement": str(arrangement.pk)}],
        "participants": [{"id": str(people[1].pk)}],
        "cells": [
            {
                "position_id": str(positions[0].pk),
                "participant_id": str(people[1].pk),
                "status": "AVAILABLE",
                "effective_part_id": str(parts[1].pk),
                "content": content,
            }
        ],
    }
    digest = fingerprint(payload)
    snapshot = GenerationSnapshot.objects.create(
        project=project,
        project_revision=project.revision,
        kind="FULL",
        payload=payload,
        sha256=digest,
        preflight_sha256=digest,
        actor=actor,
    )
    pin = SnapshotProjectContentInput.objects.create(
        snapshot=snapshot,
        position=positions[0],
        participant=people[1],
        part=parts[1],
        confirmation_id=content["confirmation_id"],
        payload=content,
    )
    original = load_project_content_pins(snapshot)
    append_logical_page(logical.pk, expected_number=1, source_page_id=page.pk, orientation=90)
    assert load_project_content_pins(snapshot) == original
    with pytest.raises(IntegrityError, match="pinned generation"), transaction.atomic():
        archive.ArchiveFile.objects.filter(pk=file.pk).update(relative_path="changed.pdf")
    with pytest.raises(ValidationError):
        pin.payload = {**content, "edition_id": str(arrangement.pk)}
        pin.full_clean()
    assert snapshot.payload == payload
