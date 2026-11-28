"""PDF text layers and raster recognition remain independent review evidence."""

import pytest

from apps.archive import models as m
from apps.archive import recognition
from apps.catalog.models import InstrumentVariant, Part, Work


@pytest.mark.parametrize(
    "ocr_title,pdf_title,expected",
    [
        ("Synthetic March", "Synthetic Polka", "CONFLICT"),
        ("Unreadable heading", "Synthetic March", "PROPOSED"),
        ("Synthetic March", "Synthetic March", "PROPOSED"),
    ],
)
def test_known_layer_and_ocr_titles_compare_without_approval(archive, ocr_title, pdf_title, expected):
    _, version, file, _ = archive
    march = Work.objects.create(title="Synthetic March")
    Work.objects.create(title="Synthetic Polka")
    item = m.OcrPageEvidence.objects.create(
        source_version=version,
        cache_key="5" * 64,
        page=0,
        evidence={
            "sha256": version.sha256,
            "cache_key": "5" * 64,
            "page": 0,
            "rules": recognition.build_rule_set().version,
            "text_layer": pdf_title,
            "words": [],
        },
    )
    candidate, _ = recognition.record_candidate(
        version.pk, filename="scan.pdf", text_lines=[ocr_title], ocr_evidence=item
    )
    file.refresh_from_db()
    assert file.candidate_state == expected
    assert file.review_state == "PENDING" and file.current_proposal_id is None
    assert "sources:pdf_text_layer" in candidate.reasons
    if expected == "CONFLICT":
        assert "work_conflict_ocr_text_layer" in candidate.reasons
        assert candidate.confidence is None
    else:
        assert candidate.proposed_work_id == march.pk


def test_conflicting_part_numbers_never_union_into_proposed_assignments(archive):
    _, version, file, _ = archive
    instrument = InstrumentVariant.objects.create(name="Posaune", transposition="C")
    Part.objects.create(instrument=instrument, code="2")
    Part.objects.create(instrument=instrument, code="3")
    item = m.OcrPageEvidence.objects.create(
        source_version=version,
        cache_key="6" * 64,
        page=0,
        evidence={
            "sha256": version.sha256,
            "cache_key": "6" * 64,
            "page": 0,
            "rules": recognition.build_rule_set().version,
            "text_layer": "Posaune III",
            "words": [],
        },
    )
    candidate, parts = recognition.record_candidate(
        version.pk, filename="scan.pdf", text_lines=["Posaune II"], ocr_evidence=item
    )
    file.refresh_from_db()
    assert file.candidate_state == "CONFLICT"
    assert "part_conflict_ocr_text_layer" in candidate.reasons
    assert parts == [] and candidate.confidence is None
