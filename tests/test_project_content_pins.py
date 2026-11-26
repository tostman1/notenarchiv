from io import BytesIO

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from pypdf import PdfReader

from apps.archive import models as archive
from apps.archive.content_geometry_services import append_logical_page
from apps.archive.content_services import confirm_content, inspect_content, propose_content
from apps.exports.content_inputs import capture_content
from apps.exports.models import GenerationSnapshot, SnapshotProjectContentInput
from apps.exports.project_content_generation import personal_content_pieces
from apps.exports.project_content_inputs import load_project_content_pins
from apps.projects.preflight_services import fingerprint
from core.pdf import Processor
from tests.test_editions import edition_inputs as legacy_inputs
from tests.test_resolution import resolver_inputs as resolution_inputs

edition_inputs = legacy_inputs
resolver_inputs = resolution_inputs


@pytest.mark.django_db
def test_historical_project_content_cell_is_protected(resolver_inputs, tmp_path):
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
        "positions": [
            {
                "id": str(positions[0].pk),
                "arrangement": str(arrangement.pk),
                "order": 1,
                "title": "Synthetic pinned title",
            },
            {"id": str(positions[1].pk), "arrangement": str(arrangement.pk), "order": 2, "title": "Missing"},
            {"id": str(positions[2].pk), "arrangement": "None", "order": 3, "title": "Reserve"},
        ],
        "participants": [{"id": str(people[1].pk)}],
        "cells": [
            {
                "position_id": str(positions[0].pk),
                "participant_id": str(people[1].pk),
                "status": "AVAILABLE",
                "effective_part_id": str(parts[1].pk),
                "content": content,
            },
            {"position_id": str(positions[1].pk), "participant_id": str(people[1].pk), "status": "MISSING"},
            {"position_id": str(positions[2].pk), "participant_id": str(people[1].pk), "status": "RESERVE"},
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
        acknowledgements=[f"{positions[1].pk}:{people[1].pk}"],
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
    scratch = tmp_path / "project-content"
    scratch.mkdir(mode=0o700)
    rendered = personal_content_pieces(snapshot, people[1].pk, Processor(scratch))
    assert len(rendered) == 3 and rendered[0]["number"] == 1
    assert [(piece["number"], piece["state"]) for piece in rendered] == [(1, "MUSIC"), (2, "MISSING"), (3, "RESERVE")]
    assert rendered[0]["title"] == "Synthetic pinned title"
    assert len(PdfReader(BytesIO(rendered[0]["data"])).pages) == 1
    assert original[(str(positions[0].pk), str(people[1].pk))].inputs[0].orientation == 0
    with (
        pytest.raises(IntegrityError, match="immutable generation"),
        transaction.atomic(),
        connection.cursor() as cursor,
    ):
        cursor.execute(
            "UPDATE exports_snapshotprojectcontentinput SET part_id=%s WHERE id=%s", [parts[0].pk.hex, pin.pk.hex]
        )
    snapshot.preflight_sha256 = "0" * 64
    with pytest.raises(ValidationError, match="fingerprint"):
        load_project_content_pins(snapshot)
    snapshot.preflight_sha256 = snapshot.sha256
    with pytest.raises(IntegrityError, match="pinned generation"), transaction.atomic():
        archive.ArchiveFile.objects.filter(pk=file.pk).update(relative_path="changed.pdf")
    with pytest.raises(ValidationError):
        pin.payload = {**content, "edition_id": str(arrangement.pk)}
        pin.full_clean()
    assert snapshot.payload == payload
