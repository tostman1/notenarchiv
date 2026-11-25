"""Source aliases and canonical links cannot silently disappear during rebaseline."""

import pytest

from scripts.check_requirements import EXPECTED_ALIASES, ROOT, validate


def documents():
    return [
        (ROOT / name).read_text(encoding="utf-8")
        for name in ("REQUIREMENTS.md", "IMPLEMENTATION_PLAN.md", "ARCHITECTURE.md", "docs/REQUIREMENTS_CROSSWALK.md")
    ]


def test_repository_traceability_structure_is_complete():
    result = validate(*documents())
    assert result["result"] == "success", result["errors"]
    assert result["source_aliases"] == len(EXPECTED_ALIASES)


@pytest.mark.parametrize("change", ["missing", "duplicate", "empty"])
def test_alias_mapping_regressions_are_rejected(change):
    inputs = documents()
    row = next(line for line in inputs[3].splitlines() if line.startswith("| REF-36 "))
    replacement = {"missing": "", "duplicate": row + "\n" + row, "empty": "| REF-36 | | |"}[change]
    inputs[3] = inputs[3].replace(row, replacement)
    result = validate(*inputs)
    assert result["result"] == "mismatch"
    assert any("REF-36" in error for error in result["errors"])


def test_dangling_identifiers_evidence_and_duplicate_headings_are_rejected():
    inputs = documents()
    inputs[0] += "\n## 1. Purpose and scope\n"
    inputs[3] += "\nAR-99 WP-99 tests/nonexistent_evidence.py\n"
    errors = validate(*inputs)["errors"]
    assert any("AR-99" in error for error in errors)
    assert any("WP-99" in error for error in errors)
    assert any("nonexistent_evidence.py" in error for error in errors)
    assert any("Duplicate requirements heading" in error for error in errors)
