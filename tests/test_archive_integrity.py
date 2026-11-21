"""Negative metadata, reference retention and database constraint cases."""

import copy
import uuid

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError

from apps.archive import models as m
from apps.archive import services as s
from apps.archive.validation import bounded_json, page_metadata, region_metadata
from apps.catalog import models as catalog
from apps.catalog.services import save_record
from tests.archive_fixtures import PAGE
from tests.test_archive_workflow import confirm, draft, inspect, reviewed_inputs  # noqa: F401


def test_history_pins_source_catalog_actor_jobs_and_ledger(reviewed_inputs):  # noqa: F811
    folder, version, file, actor, _other, arrangement, parts = reviewed_inputs
    file = confirm(file, draft(file, actor, arrangement, parts[:2]), actor)
    operation = file.publication_operation
    for record in [
        folder,
        version.source_file,
        version,
        arrangement,
        parts[0],
        actor,
        operation.job,
        operation.attempt_record,
        operation.intent,
        file.approved_proposal,
    ]:
        with pytest.raises(ProtectedError):
            type(record).objects.filter(pk=record.pk).delete()
    with pytest.raises(ValidationError):
        file.delete()
    assert m.ArchiveFile.objects.usable().filter(pk=file.pk).exists()


def test_sealed_snapshots_inspections_and_audits_cannot_be_rewritten(reviewed_inputs):  # noqa: F811
    _folder, _version, file, actor, _other, arrangement, parts = reviewed_inputs
    proposal = draft(file, actor, arrangement, parts[:1])
    inspection = inspect(file, proposal, actor)
    with pytest.raises(ValidationError):
        m.ProposalPart.objects.create(proposal=proposal, part=parts[1])
    proposal.arrangement = None
    with pytest.raises(ValidationError):
        proposal.save()
    inspection.inspected_sha256 = "0" * 64
    with pytest.raises(ValidationError):
        inspection.save()
    event = m.AuditEvent.objects.filter(archive_file=file).first()
    with pytest.raises(ValidationError):
        event.save()


def test_source_observation_reuses_old_hash_without_replacing_validation(archive):
    folder, version, file, _data = archive
    newer, created = s.observe_version(folder.pk, "Synthetic/scan.pdf", sha256="1" * 64, byte_size=500, mtime_ns=2000)
    assert created and newer.pk != version.pk
    source = m.SourceFile.objects.get(pk=version.source_file_id)
    assert source.presence == "CHANGED" and source.current_version_id == newer.pk
    same, created = s.observe_version(
        folder.pk, "Synthetic/scan.pdf", sha256=version.sha256, byte_size=version.byte_size, mtime_ns=3000
    )
    assert not created and same.pk == version.pk and same.source_mtime_ns == 1000
    assert same.pdf_state == "VALID" and same.page_info == [PAGE]
    for field, value in [
        ("sha256", "2" * 64),
        ("byte_size", 100),
        ("source_mtime_ns", 1),
        ("pdf_state", "INVALID"),
        ("page_info", []),
    ]:
        version.refresh_from_db()
        setattr(version, field, value)
        with pytest.raises(ValidationError):
            version.save()
    assert file.source_version_id == same.pk


def test_same_content_elsewhere_can_have_independent_arrangement_proposals(reviewed_inputs):  # noqa: F811
    folder, version, file, actor, _other, arrangement, parts = reviewed_inputs
    second = save_record(catalog.Arrangement(work=arrangement.work, edition="Synthetic other edition"))
    m.FolderArrangementProposal.objects.create(folder=folder, arrangement=arrangement)
    m.FolderArrangementProposal.objects.create(folder=folder, arrangement=second)
    other, _created = s.observe_version(
        folder.pk,
        "Synthetic/other.pdf",
        sha256=version.sha256,
        byte_size=version.byte_size,
        pdf_state="VALID",
        page_info=[PAGE],
    )
    other_file = s.register_base(other.pk, "_Ungeprueft/other.pdf")
    first_draft = draft(file, actor, arrangement, parts[:1])
    second_draft = draft(other_file, actor, second, parts[1:2])
    assert first_draft.arrangement_id != second_draft.arrangement_id
    candidate = m.RecognitionCandidate.objects.create(
        source_version=version,
        archive_file=file,
        input_sha256=version.sha256,
        method="FILENAME",
        proposed_arrangement=arrangement,
        confidence=1,
        rule_version="synthetic-v1",
    )
    m.CandidatePart.objects.create(candidate=candidate, part=parts[0])
    candidate.sealed = True
    candidate.save()
    with pytest.raises(ValidationError):
        m.CandidatePart.objects.create(candidate=candidate, part=parts[1])
    candidate.confidence = 0.5
    with pytest.raises(ValidationError):
        candidate.save()
    file.refresh_from_db()
    assert file.arrangement_id is None and file.review_state == "PENDING"
    assert not file.assignments.exists()
    assert not m.ReviewInspection.objects.filter(proposal__archive_file=file).exists()
    assert not m.ArchiveFile.objects.usable().exists()


def test_database_constraints_reject_unsafe_states_without_model_validation(archive):
    folder, version, file, _data = archive
    mutations = [
        (m.SourceFolder, folder.pk, {"file_count": 1, "indexed_count": 2}),
        (m.SourceFolder, folder.pk, {"index_state": "CONFIRMED"}),
        (m.SourceFile, version.source_file_id, {"presence": "INDEXED"}),
        (m.SourceVersion, version.pk, {"pdf_state": "CONFIRMED"}),
        (m.ArchiveFile, file.pk, {"review_state": "CONFIRMED"}),
        (m.ArchiveFile, file.pk, {"publication_state": "AVAILABLE"}),
        (m.ArchiveFile, file.pk, {"root_kind": "PROCESSED"}),
    ]
    for model, pk, change in mutations:
        with pytest.raises(IntegrityError), transaction.atomic():
            model.objects.filter(pk=pk).update(**change)
    with pytest.raises(ValidationError):
        m.AuditEvent.objects.create(event="VALIDATED", source_version=version, archive_file=file)
    with pytest.raises(ValidationError):
        m.AuditEvent.objects.create(event="VALIDATED")
    file.source_version_id = uuid.uuid4()
    with pytest.raises(ValidationError):
        file.full_clean()


def test_casefolded_destination_keys_protect_distinct_source_versions(archive):
    folder, version, file, _data = archive
    second, _ = s.observe_version(
        folder.pk,
        "Synthetic/second.pdf",
        sha256=version.sha256,
        byte_size=version.byte_size,
        pdf_state="VALID",
        page_info=[PAGE],
    )
    with pytest.raises(ValidationError):
        s.register_base(second.pk, file.relative_path.upper())
    assert not m.ArchiveFile.objects.filter(source_version=second).exists()


def test_derivatives_are_separate_and_retain_base_provenance(archive):
    _folder, version, file, _data = archive
    derivative = m.ArchiveFile.objects.create(
        source_version=version,
        root_kind="PROCESSED",
        relative_path="Synthetic/derived.pdf",
        sha256="2" * 64,
        byte_size=512,
        kind="DERIVATIVE",
        derived_from=file,
        processing_profile="synthetic",
        processing_version="1",
    )
    assert derivative.sha256 != file.sha256 and derivative.review_state == "PENDING"
    derivative.processing_version = "2"
    with pytest.raises(ValidationError):
        derivative.save()
    derivative.processing_version = "1"
    derivative.derived_from = derivative
    with pytest.raises(ValidationError):
        derivative.save()


@pytest.mark.parametrize(
    "mutation",
    [
        {"rotation": 45},
        {"width_points": float("nan")},
        {"user_unit": 0},
        {"crop_box": [0, 0, 0, 100]},
        {"height_points": 14401},
        {"media_box": [False, 0, 1, 2]},
    ],
)
def test_invalid_page_metadata_is_rejected(mutation):
    page = copy.deepcopy(PAGE)
    page.update(mutation)
    with pytest.raises(ValidationError):
        page_metadata([page])


@pytest.mark.parametrize(
    "value",
    [
        {"page": 1000, "box": [0, 0, 1, 1], "unit": "POINTS"},
        {"page": 0, "box": [0, 0, 2, 1], "unit": "NORMALIZED"},
        {"page": 0, "box": [0, 0, float("inf"), 1], "unit": "PIXELS"},
    ],
)
def test_invalid_recognition_regions_are_rejected(value):
    with pytest.raises(ValidationError):
        region_metadata(value)


def test_json_metadata_is_bounded_and_finite():
    for value in [{"value": float("nan")}, {"text": "x" * 16384}]:
        with pytest.raises(ValidationError):
            bounded_json(value)
