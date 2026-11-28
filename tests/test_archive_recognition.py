"""Recognition services: rule sets, comparison verdicts and evidence (WP-19).

Synthetic catalog rows only. No OCR, no files, no approvals: recognition
records candidates and the file's independent candidate_state.
"""

import pytest
from django.core.exceptions import ValidationError

from apps.archive import models as m
from apps.archive import recognition as rec
from apps.catalog.models import (
    InstrumentAlias,
    InstrumentVariant,
    Part,
    Work,
    WorkAlias,
)


@pytest.fixture
def catalog(db):
    clar_a = InstrumentVariant.objects.create(name="Klarinette", transposition="A")
    clar_b = InstrumentVariant.objects.create(name="Klarinette", transposition="Bb")
    posaune = InstrumentVariant.objects.create(name="Posaune", transposition="C")
    tuba = InstrumentVariant.objects.create(name="Tuba", transposition="Es")
    clarinette = InstrumentVariant.objects.create(name="Clarinet", transposition="Bb")
    work = Work.objects.create(title="Einzug der Garde")
    WorkAlias.objects.create(alias="Einzug", work=work)
    clarinette_alias = InstrumentAlias.objects.create(alias="Clarinet A", instrument=clar_a)
    return {
        "clar_a": clar_a,
        "clar_b": clar_b,
        "posaune": posaune,
        "tuba": tuba,
        "clarinette": clarinette,
        "work": work,
        "clarinette_alias": clarinette_alias,
    }


def parts(catalog, variant, codes):
    created = []
    for code in codes:
        created.append(Part.objects.create(instrument=variant, code=code))
    return created


def test_rule_set_version_is_stable_and_bounded(catalog):
    rules_a = rec.build_rule_set()
    rules_b = rec.build_rule_set()
    assert rules_a.version == rules_b.version
    assert rules_a.version.startswith("wp19-")
    # Inactive rows never enter the rule set.
    catalog["posaune"].active = False
    catalog["posaune"].save()
    rules_c = rec.build_rule_set()
    assert rules_c.version != rules_a.version
    assert all(variant["name_key"] != "posaune" for variant in rules_c.variants)


def test_rule_version_tracks_alias_target_and_equal_title_identity(catalog):
    original = rec.build_rule_set().version
    alias = catalog["clarinette_alias"]
    alias.instrument = catalog["clar_b"]
    alias.save()
    retargeted = rec.build_rule_set().version
    assert retargeted != original
    duplicate = Work.objects.create(title=catalog["work"].title)
    assert rec.build_rule_set().version != retargeted
    work_alias = WorkAlias.objects.get(alias="Einzug")
    before = rec.build_rule_set().version
    work_alias.work = duplicate
    work_alias.save()
    assert rec.build_rule_set().version != before


def test_rule_version_tracks_part_instrument_identity(catalog):
    part = Part.objects.create(instrument=catalog["clar_a"], code="1")
    before = rec.build_rule_set().version
    part.instrument = catalog["clar_b"]
    part.save()
    assert rec.build_rule_set().version != before


def test_match_instrument_pitch_disambiguates(catalog):
    rules = rec.build_rule_set()
    variants, part_ids, exact = rec.match_instrument("Klarinette A 1", rules)
    assert [variant for variant in variants] == [catalog["clar_a"].pk]
    assert part_ids == [] and exact is True
    variants, _, _ = rec.match_instrument("Klarinette Bb 2", rules)
    assert [variant for variant in variants] == [catalog["clar_b"].pk]
    # A bare ambiguous name stays ambiguous, never silently narrowed.
    variants, _, exact = rec.match_instrument("Klarinette", rules)
    assert len(variants) == 2 and exact is False


def test_match_instrument_uses_instrument_aliases(catalog):
    rules = rec.build_rule_set()
    variants, part_ids, exact = rec.match_instrument("Clarinet A", rules)
    assert [variant for variant in variants] == [catalog["clar_a"].pk] and part_ids == [] and exact is True


def test_match_work_exact_alias_and_unknown(catalog):
    rules = rec.build_rule_set()
    work_id, exact = rec.match_work("Einzug der Garde", rules)
    assert work_id == catalog["work"].pk and exact is True
    work_id, exact = rec.match_work("Einzug", rules)
    assert work_id == catalog["work"].pk and exact is True  # Exact alias key hit.
    assert rec.match_work("Unbekanntes Lied", rules) == (None, False)


def test_candidate_proposed_with_parts_from_filename_and_text(catalog, db, archive):
    p1, p2 = parts(catalog, catalog["posaune"], ["1", "2"])
    folder, version, file, _data = archive
    rec.record_candidate(
        version.pk,
        filename="Einzug der Garde - Posaune 1.pdf",
        text_lines=["Einzug der Garde", "Posaune 1", "March"],
    )
    candidate = m.RecognitionCandidate.objects.get()
    file.refresh_from_db()
    assert file.candidate_state == m.ArchiveFile.CandidateState.PROPOSED
    assert candidate.method == "TEXT_LAYER"
    assert candidate.proposed_work_id == catalog["work"].pk
    assert candidate.confidence is not None and 0 < candidate.confidence <= 1
    assert candidate.sealed is True
    assert [str(part.part_id) for part in candidate.parts.all()] == [str(p1.pk)]
    # Re-analysis under the same rule set is idempotent.
    candidate_again, _parts = rec.record_candidate(
        version.pk, filename="Einzug der Garde - Posaune 1.pdf", text_lines=["Einzug der Garde", "Posaune 1"]
    )
    assert candidate_again.pk == candidate.pk and m.RecognitionCandidate.objects.count() == 1


def test_candidate_unknown_for_unresolvable_name(catalog, db, archive):
    folder, version, file, _data = archive
    rec.record_candidate(version.pk, filename="Scan ohne Namen.pdf")
    file.refresh_from_db()
    candidate = m.RecognitionCandidate.objects.get()
    assert file.candidate_state == m.ArchiveFile.CandidateState.UNKNOWN
    assert candidate.method == "FILENAME"
    assert candidate.proposed_work_id is None
    assert candidate.confidence is None
    assert "work_unresolved" in candidate.reasons and "instrument_unresolved" in candidate.reasons


def test_candidate_conflict_when_sources_disagree(catalog, db, archive):
    parts(catalog, catalog["posaune"], ["1", "2"])
    folder, version, file, _data = archive
    rec.record_candidate(
        version.pk,
        filename="Einzug der Garde - Posaune 1.pdf",
        text_lines=["Einzug der Garde", "Posaune 2"],
    )
    file.refresh_from_db()
    candidate = m.RecognitionCandidate.objects.get()
    assert file.candidate_state == m.ArchiveFile.CandidateState.CONFLICT
    assert candidate.confidence is None
    assert "part_conflict_between_sources" in candidate.reasons
    assert candidate.parts.count() == 0


def test_candidate_conflict_for_ambiguous_instrument(catalog, db, archive):
    folder, version, file, _data = archive
    rec.record_candidate(version.pk, filename="Einzug der Garde - Klarinette.pdf")
    file.refresh_from_db()
    candidate = m.RecognitionCandidate.objects.get()
    assert file.candidate_state == m.ArchiveFile.CandidateState.CONFLICT
    assert "instrument_ambiguous" in candidate.reasons


def test_combined_parts_keep_all_parts(catalog, db, archive):
    tuba1, tuba2 = parts(catalog, catalog["tuba"], ["1", "2"])
    folder, version, file, _data = archive
    rec.record_candidate(version.pk, filename="Einzug der Garde - Tuba 1-2.pdf")
    file.refresh_from_db()
    candidate = m.RecognitionCandidate.objects.get()
    assert candidate.parts.count() == 2
    assert {str(part.part_id) for part in candidate.parts.all()} == {str(tuba1.pk), str(tuba2.pk)}
    assert file.candidate_state == m.ArchiveFile.CandidateState.PROPOSED


def test_roman_numeral_filename_matches_digit_part(catalog, db, archive):
    part_2 = parts(catalog, catalog["posaune"], ["2"])[0]
    folder, version, file, _data = archive
    rec.record_candidate(version.pk, filename="Einzug der Garde - Posaune II.pdf")
    file.refresh_from_db()
    candidate = m.RecognitionCandidate.objects.get()
    assert [str(part.part_id) for part in candidate.parts.all()] == [str(part_2.pk)]
    assert file.candidate_state == m.ArchiveFile.CandidateState.PROPOSED


def test_roman_combined_parts_trombone_two_three(catalog, db, archive):
    p2, p3 = parts(catalog, catalog["posaune"], ["2", "3"])
    folder, version, file, _data = archive
    # "Trombone II/III" is one PDF assigned to both parts (AR-10); the
    # filename-safe combined form is the hyphen.
    rec.record_candidate(version.pk, filename="Einzug der Garde - Posaune II-III.pdf")
    file.refresh_from_db()
    candidate = m.RecognitionCandidate.objects.get()
    assert candidate.parts.count() == 2
    assert {str(part.part_id) for part in candidate.parts.all()} == {str(p2.pk), str(p3.pk)}
    assert file.candidate_state == m.ArchiveFile.CandidateState.PROPOSED


def test_unicode_and_notation_spelling_normalization(catalog, db, archive):
    p1 = parts(catalog, catalog["posaune"], ["1"])[0]
    folder, version, file, _data = archive
    # NFKC: full-width spelling normalizes to the same catalog keys.
    rec.record_candidate(version.pk, filename="Ｅｉｎｚｕｇ der Garde - Ｐｏｓａｕｎｅ １.pdf")
    file.refresh_from_db()
    candidate = m.RecognitionCandidate.objects.get()
    assert [str(part.part_id) for part in candidate.parts.all()] == [str(p1.pk)]
    assert file.candidate_state == m.ArchiveFile.CandidateState.PROPOSED


def test_new_rule_change_records_new_candidate_without_touching_history(catalog, db, archive):
    folder, version, file, _data = archive
    rec.record_candidate(version.pk, filename="Einzug der Garde - Posaune 1.pdf")
    first = m.RecognitionCandidate.objects.get()
    InstrumentVariant.objects.create(name="Pauke", transposition="C")
    candidate, candidate_parts = rec.record_candidate(version.pk, filename="Einzug der Garde - Posaune 1.pdf")
    assert m.RecognitionCandidate.objects.count() == 2
    assert candidate.pk != first.pk
    assert candidate.rule_version != first.rule_version
    assert first.sealed is True
    file.refresh_from_db()
    assert file.candidate_state in (
        m.ArchiveFile.CandidateState.PROPOSED,
        m.ArchiveFile.CandidateState.CONFLICT,
        m.ArchiveFile.CandidateState.UNKNOWN,
    )


def test_recognition_never_approves(catalog, db, archive):
    parts(catalog, catalog["posaune"], ["1"])
    folder, version, file, _data = archive
    rec.record_candidate(
        version.pk,
        filename="Einzug der Garde - Posaune 1.pdf",
        text_lines=["Einzug der Garde", "Posaune 1"],
    )
    file.refresh_from_db()
    assert file.review_state == m.ArchiveFile.ReviewState.PENDING
    assert file.publication_state == m.ArchiveFile.PublicationState.UNPUBLISHED
    assert file.approved_proposal_id is None
    assert file.assignments.count() == 0
    # Confidence 1 alone cannot approve; candidates cannot propose directly.
    assert m.ArchiveProposal.objects.count() == 0


def test_candidate_is_immutable(catalog, db, archive):
    folder, version, file, _data = archive
    candidate, _parts = rec.record_candidate(version.pk, filename="Einzug der Garde - Posaune 1.pdf")
    candidate.confidence = 0.9
    with pytest.raises(ValidationError):
        candidate.save()
    candidate.sealed = False
    with pytest.raises(ValidationError):
        candidate.save()
    candidate = m.RecognitionCandidate.objects.get(pk=candidate.pk)
    assert candidate.sealed is True


def test_excerpt_is_bounded(catalog, db, archive):
    folder, version, file, _data = archive
    rec.record_candidate(version.pk, filename="Einzug der Garde - Posaune 1.pdf", text_lines=["Einzug der Garde"])
    candidate = m.RecognitionCandidate.objects.get()
    assert len(candidate.excerpt) <= 4096
    assert "Dateiname:" in candidate.excerpt
