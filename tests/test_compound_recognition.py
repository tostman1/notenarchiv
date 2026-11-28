from uuid import uuid4

import pytest

from apps.archive.compound_recognition import headings
from apps.archive.recognition import RuleSet


def word(text, block, left=0):
    return {"text": text, "line": [1, block, 1, 1], "box": [left, 10, left + 20, 30], "confidence": 0.9}


def test_side_by_side_headings_preserve_identity_and_locations():
    first, second = uuid4(), uuid4()
    rules = RuleSet("test", works={"first march": [first], "second polka": [second]})
    evidence = {
        "page": 2,
        "words": [word("First", 1), word("March", 1, 25), word("Second", 2, 100), word("Polka", 2, 125)],
    }
    result = headings(evidence, rules)
    assert [entry.work_id for entry in result] == [first, second]
    assert [entry.box for entry in result] == [(0, 10, 45, 30), (100, 10, 145, 30)]
    assert all(entry.page == 2 for entry in result)


def test_repeated_titles_remain_separate_and_unknown_lines_are_not_boundaries():
    work = uuid4()
    rules = RuleSet("test", works={"march": [work]})
    result = headings({"page": 0, "words": [word("March", 1), word("Unknown", 2), word("March", 3)]}, rules)
    assert [entry.work_id for entry in result] == [work, work]


def test_equal_titles_do_not_merge_catalog_identities():
    rules = RuleSet("test", works={"march": [uuid4(), uuid4()]})
    result = headings({"page": 0, "words": [word("March", 1)]}, rules)
    assert len(result) == 1
    assert result[0].ambiguous and result[0].work_id is None


def test_exact_alias_matches_but_prefixes_are_not_compound_headings():
    work = uuid4()
    rules = RuleSet("test", works={"march extended": [work]}, work_aliases={"alias": work})
    result = headings({"page": 0, "words": [word("March", 1), word("Alias", 2)]}, rules)
    assert [entry.text for entry in result] == ["Alias"]


def test_legacy_words_without_line_identities_remain_ordinary_evidence():
    rules = RuleSet("test", works={"march": [uuid4()]})
    assert headings({"page": 0, "words": [{"text": "March", "box": [0, 0, 10, 10]}]}, rules) == []


def test_heading_observations_have_a_fixed_output_bound():
    rules = RuleSet("test", works={"march": [uuid4()]})
    result = headings({"page": 0, "words": [word("March", block) for block in range(200)]}, rules)
    assert len(result) == 128


@pytest.mark.parametrize("text", ["125. March", "125) March", "125 March", "Nr. 125 March", "No. 125 March"])
def test_printed_numbers_are_evidence_not_identity(text):
    work = uuid4()
    rules = RuleSet("test", works={"march": [work]})
    result = headings({"page": 0, "words": [word(text, 1)]}, rules)
    assert len(result) == 1
    assert result[0].text == text and result[0].work_id == work
    assert result[0].printed_number == "125"


def test_number_in_actual_work_title_wins_over_numbered_heading_interpretation():
    original, remainder = uuid4(), uuid4()
    rules = RuleSet("test", works={"1812 overture": [original], "overture": [remainder]})
    result = headings({"page": 0, "words": [word("1812 Overture", 1)]}, rules)
    assert result[0].work_id == original and result[0].printed_number is None


def test_same_printed_number_never_merges_different_works_or_resolves_equal_titles():
    first, second = uuid4(), uuid4()
    rules = RuleSet("test", works={"march": [first], "polka": [second], "suite": [uuid4(), uuid4()]})
    result = headings({"page": 0, "words": [word("1. March", 1), word("1. Polka", 2), word("1. Suite", 3)]}, rules)
    assert [entry.work_id for entry in result] == [first, second, None]
    assert result[-1].ambiguous
    assert [entry.printed_number for entry in result] == ["1", "1", "1"]


@pytest.mark.parametrize("evidence", [{"page": True}, {"page": 500}, {"page": 0, "words": [{}] * 2049}])
def test_compound_observations_fail_closed_at_bounds(evidence):
    with pytest.raises(ValueError):
        headings(evidence, RuleSet("test"))


@pytest.mark.parametrize(
    "bad",
    [
        word("March", 1) | {"line": [True, 1, 1, 1]},
        word("March", 1) | {"box": [0, 0, float("nan"), 5]},
        word("March", 1) | {"text": "x" * 513},
    ],
)
def test_malformed_native_observations_fail_closed(bad):
    with pytest.raises(ValueError):
        headings({"page": 0, "words": [bad]}, RuleSet("test"))
