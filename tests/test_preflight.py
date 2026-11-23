"""Preflight/matrix parity, explicit missing decisions and fail-closed input checks."""

import uuid

import pytest
from django.core.exceptions import ValidationError
from django.test import Client
from django.urls import reverse

from apps.projects import models as m
from apps.projects.matrix_services import matrix_page
from apps.projects.preflight_services import build_report, report_token, validate_acknowledgement
from tests.test_resolution import resolver_inputs as _resolution_fixture

resolver_inputs = _resolution_fixture


def test_report_identical_to_matrix_missing_ambiguous_and_reserve(resolver_inputs):
    actor, project, *_ = resolver_inputs
    report = build_report(project.pk)
    matrix = matrix_page(project.pk)
    assert [cell["resolution"] for row in report.rows for cell in row["cells"]] == [
        cell["resolution"] for row in matrix["rows"] for cell in row["cells"]
    ]
    assert report.blocking == 2 and len(report.missing_keys) == 4
    assert len(report.payload["positions"]) == 3
    with pytest.raises(ValidationError, match="Blockierende"):
        validate_acknowledgement(report, report_token(report, actor), list(report.missing_keys), actor)
    assert project.revision == 1


def test_missing_ack_requires_each_cell_and_no_generation_job(resolver_inputs):
    actor, project, _arr, parts, people, positions, *_ = resolver_inputs
    report = build_report(project.pk, participant_ids=[people[0].pk])
    token = report_token(report, actor)
    with pytest.raises(ValidationError, match="Jede fehlende"):
        validate_acknowledgement(report, token, [], actor)
    assert validate_acknowledgement(report, token, sorted(report.missing_keys), actor)
    from apps.jobs.models import Job

    assert not Job.objects.filter(kind="GENERATE").exists()


def test_stale_selection_and_actor_tokens_rejected(resolver_inputs):
    actor, project, _arr, parts, people, *_ = resolver_inputs
    report = build_report(project.pk, participant_ids=[people[0].pk])
    token = report_token(report, actor)
    m.Project.objects.filter(pk=project.pk).update(revision=2)
    changed = build_report(project.pk, participant_ids=[people[0].pk])
    with pytest.raises(ValidationError, match="geändert"):
        validate_acknowledgement(changed, token, sorted(changed.missing_keys), actor)
    with pytest.raises(ValidationError, match="ungültig"):
        validate_acknowledgement(changed, "forged", [], actor)
    with pytest.raises(ValidationError):
        build_report(project.pk, participant_ids=[uuid.uuid4()])
    with pytest.raises(ValidationError):
        build_report(project.pk, position_ids=[])
    with pytest.raises(ValidationError, match="mehrfach"):
        build_report(project.pk, participant_ids=[people[0].pk, people[0].pk])


def test_corrupt_confirmed_copy_blocks_and_is_actionable(resolver_inputs, settings):
    actor, project, _arr, parts, people, positions, first, *_ = resolver_inputs
    m.PartOverride.objects.create(
        project=project,
        position=positions[0],
        participant=people[2],
        desired_part=parts[1],
        edition=first.assignments.get(),
    )
    report = build_report(project.pk, participant_ids=[people[2].pk], position_ids=[positions[0].pk])
    assert report.blocking == 0 and report.rows[0]["cells"][0]["inspection"]["pages"]
    (settings.CURATED_DIR / first.relative_path).write_bytes(b"corrupt synthetic")
    report = build_report(project.pk, participant_ids=[people[2].pk], position_ids=[positions[0].pk])
    assert report.blocking == 1 and report.rows[0]["cells"][0]["resolution"].status == "CORRUPT"


def test_pdf_parser_failure_is_blocking_not_missing(resolver_inputs, monkeypatch):
    actor, project, _arr, parts, people, positions, first, *_ = resolver_inputs
    m.PartOverride.objects.create(
        project=project,
        position=positions[0],
        participant=people[2],
        desired_part=parts[1],
        edition=first.assignments.get(),
    )
    from apps.projects import preflight_services as service
    from core.pdf import PdfError

    def malformed(*args):
        raise PdfError("INVALID_PDF")

    monkeypatch.setattr(service, "inspect_file", malformed)
    report = build_report(project.pk, participant_ids=[people[2].pk], position_ids=[positions[0].pk])
    assert report.blocking == 1 and not report.missing_keys


def test_preflight_auth_csrf_subset_ack_and_no_project_mutation(resolver_inputs, client):
    actor, project, _arr, parts, people, positions, *_ = resolver_inputs
    url = reverse("project_preflight", args=[project.pk])
    assert client.get(url).status_code == 302
    client.force_login(actor)
    assert client.get(url).status_code == 200
    values = {"participants": [str(people[0].pk)], "positions": [str(positions[0].pk)], "action": "inspect"}
    response = client.post(url, values)
    assert response.status_code == 200 and "Noten fehlen" in response.content.decode()
    report = response.context["report"]
    values.update(action="acknowledge", token=report_token(report, actor))
    assert client.post(url, values).status_code == 409
    values["acknowledgements"] = sorted(report.missing_keys)
    response = client.post(url, values)
    assert response.status_code == 200 and response.context["acknowledged"]
    assert project.revision == 1 and project.positions.count() == 3
    csrf = Client(enforce_csrf_checks=True)
    csrf.force_login(actor)
    assert csrf.post(url, values).status_code == 403


def test_inspection_once_per_shared_file_and_limits(resolver_inputs, monkeypatch):
    actor, project, _arr, parts, people, positions, first, *_ = resolver_inputs
    for position in positions[:2]:
        m.PartOverride.objects.create(
            project=project,
            position=position,
            participant=people[2],
            desired_part=parts[1],
            edition=first.assignments.get(),
        )
    from apps.projects import preflight_services as service

    original, calls = service.inspect_file, []

    def inspect(file, *args):
        calls.append(file.pk)
        return original(file, *args)

    monkeypatch.setattr(service, "inspect_file", inspect)
    report = build_report(project.pk, participant_ids=[people[2].pk])
    assert calls == [first.pk] and report.blocking == 0
    monkeypatch.setattr(service, "MAX_BYTES", 1)
    with pytest.raises(ValidationError, match="Prüfumfang"):
        build_report(project.pk, participant_ids=[people[2].pk])


def test_unconfirmed_conflicting_candidate_is_notice_never_music(resolver_inputs):
    actor, project, arr, parts, people, positions, first, second, make = resolver_inputs
    from apps.archive import models as archive
    from tests.test_archive_workflow import draft

    pending = make(8, confirmed=False)
    draft(pending, actor, arr, [parts[0]])
    archive.ArchiveFile.objects.filter(pk=pending.pk).update(candidate_state="CONFLICT")
    report = build_report(project.pk, participant_ids=[people[0].pk])
    assert len(report.payload["pending"]) == 1
    assert report.payload["pending"][0]["candidate_state"] == "CONFLICT"
    assert len(report.missing_keys) == 2 and report.blocking == 0
    assert all(cell["resolution"].assignment_id is None for row in report.rows for cell in row["cells"])


def test_known_unavailable_input_blocks_acknowledgement(resolver_inputs):
    actor, project, arr, parts, people, positions, first, second, make = resolver_inputs
    from apps.archive import models as archive

    archive.ArchiveFile.objects.filter(pk__in=[first.pk, second.pk]).update(publication_state="CORRUPT")
    report = build_report(project.pk, participant_ids=[people[1].pk])
    assert report.blocking == 2 and not report.missing_keys
    assert report.rows[0]["cells"][0]["unavailable_input"]
    with pytest.raises(ValidationError, match="Blockierende"):
        validate_acknowledgement(report, report_token(report, actor), [], actor)


def test_layout_inspection_flags_native_a3_rotation_and_custom(resolver_inputs, tmp_path):
    actor, project, arr, parts, people, positions, first, *_ = resolver_inputs
    import hashlib
    from types import SimpleNamespace

    from apps.projects.preflight_services import inspect_file
    from tests.pdf_fixtures import A3, A4, pdf

    data = pdf(sizes=(A3, A4, (400, 300)), rotation=90)
    root = tmp_path / "synthetic-layout"
    root.mkdir()
    (root / "input.pdf").write_bytes(data)
    import time

    from django.test import override_settings

    file = SimpleNamespace(
        root_kind="CLEAN", relative_path="input.pdf", sha256=hashlib.sha256(data).hexdigest(), byte_size=len(data)
    )
    with override_settings(CURATED_DIR=root):
        result = inspect_file(file, tmp_path, time.monotonic() + 30)
    assert {"NATIVE_A3", "LANDSCAPE", "CUSTOM", "ROTATED", "MIXED"} <= set(result["flags"])
    assert len(result["pages"]) == 3


def test_malformed_pdf_with_matching_hash_fails_isolated_parser(resolver_inputs, tmp_path):
    import hashlib
    import time
    from types import SimpleNamespace

    from django.test import override_settings

    from apps.projects.preflight_services import inspect_file
    from core.pdf import PdfError

    data = b"%PDF-1.7\nnot a valid synthetic document"
    (tmp_path / "broken.pdf").write_bytes(data)
    file = SimpleNamespace(
        root_kind="CLEAN", relative_path="broken.pdf", sha256=hashlib.sha256(data).hexdigest(), byte_size=len(data)
    )
    with override_settings(CURATED_DIR=tmp_path), pytest.raises(PdfError):
        inspect_file(file, tmp_path, time.monotonic() + 30)


def test_ack_rejects_other_actor_duplicate_keys_and_foreign_keys(resolver_inputs):
    actor, project, arr, parts, people, *_ = resolver_inputs
    from django.contrib.auth import get_user_model

    other = get_user_model().objects.create_user("synthetic-other-preflight")
    report = build_report(project.pk, participant_ids=[people[0].pk])
    token = report_token(report, actor)
    keys = sorted(report.missing_keys)
    for user, choices in [(other, keys), (actor, [*keys, keys[0]]), (actor, [*keys, "foreign"])]:
        with pytest.raises(ValidationError):
            validate_acknowledgement(report, token, choices, user)


def test_withdrawn_exact_edition_is_blocking_not_substituted(resolver_inputs):
    actor, project, arr, parts, people, positions, first, *_ = resolver_inputs
    from apps.archive import models as archive

    m.PartOverride.objects.create(
        project=project,
        position=positions[0],
        participant=people[2],
        desired_part=parts[1],
        edition=first.assignments.get(),
    )
    archive.ArchiveAssignment.objects.filter(archive_file=first).update(state="WITHDRAWN")
    report = build_report(project.pk, participant_ids=[people[2].pk], position_ids=[positions[0].pk])
    assert report.blocking == 1 and not report.missing_keys
    assert report.rows[0]["cells"][0]["resolution"].status == "INVALID"
