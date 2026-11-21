"""Unit tests for the pure recognition primitives (WP-19).

Synthetic string inputs only; no catalog rows, PDFs or files are involved.
"""

from core import recognition as rec


def test_normalize_is_nfkc_whitespace_and_casefold():
    assert rec.normalize("  Trompete   B  2") == "trompete b 2"
    assert rec.normalize("Trombone\u2009II/III") == "trombone ii/iii"
    assert rec.normalize("Klarinette\u00a0A") == "klarinette a"
    assert rec.normalize(None) == ""
    assert rec.normalize("  ") == ""


def test_canonical_pitch_german_and_english_spelling():
    assert rec.canonical_pitch("B") == "Bb"
    assert rec.canonical_pitch("h") == "B"
    assert rec.canonical_pitch("C") == "C"
    assert rec.canonical_pitch("Es") == "Eb"
    assert rec.canonical_pitch("cis") == "Cs"
    assert rec.canonical_pitch("ges") == "Gb"
    assert rec.canonical_pitch("as") == "Ab"
    # Unknown tokens normalize but do not collide with known spellings.
    assert rec.canonical_pitch("X") == "x"


def test_roman_numerals_are_bounded():
    assert rec.roman_to_int("I") == 1
    assert rec.roman_to_int("iv") == 4
    assert rec.roman_to_int("III") == 3
    assert rec.roman_to_int("CMXCV") == 995
    assert rec.roman_to_int("MM") is None  # Out of the bounded part range.
    assert rec.roman_to_int("abc") is None
    assert rec.roman_to_int("") is None


def test_codes_match_numeric_and_roman_spellings():
    assert rec.codes_match("II", "2")
    assert rec.codes_match("ii", "II")
    assert rec.codes_match("1", "1")
    assert not rec.codes_match("1", "2")
    assert not rec.codes_match("solo", "2")
    # A bare single letter is pitch-ambiguous, not a numeric code.
    assert rec.codes_match("a", "a")
    assert not rec.codes_match("a", "1")


def test_split_part_code_combined_forms():
    assert rec.split_part_code("II/III") == ("ii", "iii")
    assert rec.split_part_code("1/2/3") == ("1", "2", "3")
    # Filename-safe combined codes use - or _ separators.
    assert rec.split_part_code("1-2") == ("1", "2")
    assert rec.split_part_code("II_III") == ("ii", "iii")
    assert rec.split_part_code("Div.") == ("div.",)
    assert rec.is_part_code("Trombone") is False
    assert rec.is_part_code("2") is True
    for bad in ("", "klar", "II/kla", "a/b", "1-kla"):
        try:
            rec.split_part_code(bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"expected ValueError for {bad!r}")


def test_parse_label_shapes():
    cases = {
        "Posaune 2": ("posaune", "", ("2",)),
        "Klarinette Bb 1": ("klarinette", "bb", ("1",)),
        "Klarinette A": ("klarinette", "a", ()),
        "Trombone II/III": ("trombone", "", ("ii", "iii")),
        "Tuba Es 1/2": ("tuba", "es", ("1", "2")),
        "Kontrabass": ("kontrabass", "", ()),
        "Trompete B 2": ("trompete", "b", ("2",)),
    }
    for label, (name, pitch, parts) in cases.items():
        parsed = rec.parse_label(label)
        assert (parsed.name, parsed.pitch, parsed.part_tokens) == (name, pitch, parts), label


def test_parse_label_empty_and_odd():
    assert rec.parse_label("").name == ""
    assert not rec.parse_label("   ").has_part
    # Unrecognized single letters become pitch candidates, never part codes.
    assert rec.parse_label("X Y").part_tokens == ()


def test_parts_agree_semantics():
    assert rec.parts_agree(("2",), ("2",)) == "agree"
    assert rec.parts_agree(("ii",), ("2",)) == "agree"
    # One source less specific (subset) is consistent, not a conflict.
    assert rec.parts_agree(("ii", "iii"), ("2",)) == "consistent"
    # Disjoint numeric parts are a real conflict.
    assert rec.parts_agree(("1",), ("2",)) == "conflict"
    # Missing evidence on either side is insufficient, not agreement.
    assert rec.parts_agree((), ("1",)) == "insufficient"
    assert rec.parts_agree((), ()) == "insufficient"
