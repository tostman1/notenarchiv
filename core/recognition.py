"""Pure filename and text-layer recognition primitives.

No Django, no filesystem, no OCR. Bounded string processing that turns a
filename stem and extracted text lines into musical identifications. Results
are evidence and comparison primitives only; they never approve anything.
The Django layer (``apps.archive.recognition``) resolves these against the
editable catalog rules and persists immutable candidates.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

# Built-in grammar version. Editable alias/rule provenance (catalog rows) is
# combined with this on the Django side to form the candidate rule_version.
RULE_VERSION = "v1"

_WHITESPACE = re.compile(r"\s+")

# German/English note-name -> canonical pitch class. The canonical form is a
# coarse identity used only to match a detected token against a catalog
# transposition; the catalog's own normalized key remains the primary match.
_PITCH = {
    "c": "C",
    "cis": "Cs",
    "c#": "Cs",
    "cs": "Cs",
    "d": "D",
    "des": "Db",
    "d#": "Ds",
    "ds": "Ds",
    "dis": "Ds",
    "e": "E",
    "es": "Eb",
    "eb": "Eb",
    "f": "F",
    "fis": "Fs",
    "f#": "Fs",
    "fs": "Fs",
    "g": "G",
    "ges": "Gb",
    "g#": "Gs",
    "gs": "Gs",
    "a": "A",
    "as": "Ab",
    "a#": "As",
    "ab": "Ab",
    # German convention is primary for this (German) application: H = B
    # natural, B = B-flat. English spellings are mapped alongside so either
    # input normalizes to a canonical class for comparison.
    "h": "B",
    "hb": "B",
    "h#": "B#",
    "b": "Bb",
    "bb": "Bb",
    "bes": "Bb",
}

_PITCH_TOKENS = frozenset(_PITCH)

# Roman numeral value tables.
_ROMAN_VALUE = {
    "i": 1,
    "v": 5,
    "x": 10,
    "l": 50,
    "c": 100,
    "d": 500,
    "m": 1000,
}
_ROMAN_TOKEN = re.compile(r"^[ivxlcdm]+$")

# Letter part codes that are not pitch names and not multi-letter romans.
_WORD_CODES = frozenset({"solo", "soli", "s", "divisi", "div", "div.", "1a", "1b", "2a", "2b"})


def normalize(value) -> str:
    """NFKC, single-spaced, casefolded; the same key the catalog stores."""
    if value is None:
        return ""
    text = unicodedata.normalize("NFKC", str(value))
    return _WHITESPACE.sub(" ", text).strip().casefold()


def canonical_pitch(token: str) -> str:
    """Map a detected note token to a canonical pitch class.

    Unknown tokens return their normalized form, so identical spellings still
    compare equal while genuinely different spellings do not collide.
    """
    key = normalize(token)
    return _PITCH.get(key, key)


def roman_to_int(token: str):
    """Parse a standard roman numeral to an int, or None when not one."""
    key = normalize(token)
    if not _ROMAN_TOKEN.match(key):
        return None
    total = 0
    previous = 0
    for char in reversed(key):
        value = _ROMAN_VALUE[char]
        if value < previous:
            total -= value
        else:
            total += value
            previous = value
    return total if 1 <= total <= 999 else None


def code_value(token: str):
    """Numeric value of a part code token (digits or multi-letter roman).

    A bare single letter is ambiguous (pitch vs roman) and is treated as a
    pitch elsewhere, so it yields None here.
    """
    key = normalize(token)
    if key.isdigit():
        return int(key)
    if len(key) >= 2:
        return roman_to_int(key)
    return None


def codes_match(a: str, b: str) -> bool:
    """True when two part-code tokens identify the same musical part.

    Matches by normalized string or by numeric value so ``II`` equals ``2``.
    """
    key_a, key_b = normalize(a), normalize(b)
    if key_a == key_b:
        return True
    value_a, value_b = code_value(a), code_value(b)
    return value_a is not None and value_a == value_b


def _is_word_code(token: str) -> bool:
    return normalize(token) in _WORD_CODES


def _is_code_segment(segment: str) -> bool:
    key = normalize(segment)
    if not key:
        return False
    if key.isdigit():
        return True
    if _is_word_code(key):
        return True
    # Multi-letter roman numerals are unambiguous part codes.
    return len(key) >= 2 and roman_to_int(key) is not None


def split_part_code(token: str) -> tuple[str, ...]:
    """Split a combined code like ``II/III``, ``1-2`` or ``1_2/3`` into parts.

    Raises ValueError when any segment is not a valid part-code segment.
    """
    key = normalize(token)
    if not key:
        raise ValueError("Empty part code")
    segments = re.split(r"[/\-_]", key)
    for segment in segments:
        if not _is_code_segment(segment):
            raise ValueError("Not a part-code segment")
    return tuple(segments)


def is_part_code(token: str) -> bool:
    try:
        split_part_code(token)
        return True
    except ValueError:
        return False


def _is_pitch(token: str) -> bool:
    return normalize(token) in _PITCH_TOKENS


@dataclass(frozen=True)
class ParsedLabel:
    """A pragmatic decomposition of an instrument label.

    ``name`` is the normalized instrument name (one or more words); ``pitch``
    is an optional normalized note token; ``part_tokens`` is the optional tuple
    of part-code segments (empty when no part code is present).
    """

    name: str
    pitch: str = ""
    part_tokens: tuple[str, ...] = ()
    raw: str = ""

    @property
    def has_part(self) -> bool:
        return bool(self.part_tokens)


def parse_label(label: str) -> ParsedLabel:
    """Split an instrument label into name, optional pitch and part code.

    Handles the common marching-band shapes: ``Posaune 2``, ``Klarinette A``,
    ``Klarinette Bb 1``, ``Trombone II/III``, ``Trompete B 2``. A bare single
    letter is read as a pitch, a multi-letter roman or digit as a part code.
    Unparseable inputs yield an empty part set and the full text as name.
    """
    raw = label if isinstance(label, str) else ""
    tokens = [normalize(t) for t in raw.split()]
    tokens = [t for t in tokens if t]
    if not tokens:
        return ParsedLabel(name="", raw=raw)

    index = len(tokens) - 1
    part_tokens: tuple[str, ...] = ()
    pitch = ""
    if is_part_code(tokens[index]):
        part_tokens = split_part_code(tokens[index])
        index -= 1
    if index >= 0 and _is_pitch(tokens[index]):
        pitch = tokens[index]
        index -= 1
    name = " ".join(tokens[: index + 1])
    return ParsedLabel(name=name, pitch=pitch, part_tokens=part_tokens, raw=raw)


@dataclass(frozen=True)
class Evidence:
    """A single-source musical identification produced by one evidence method."""

    method: str
    title: str = ""
    instrument: str = ""
    pitch: str = ""
    part_tokens: tuple[str, ...] = ()
    resolved: bool = False
    part_conflicts: tuple[str, ...] = ()


def parts_agree(a: tuple, b: tuple) -> str:
    """Compare two resolved part-code sets (numeric where possible).

    Returns ``agree`` when equal, ``consistent`` when one is a subset of the
    other (one source less specific), and ``conflict`` otherwise. Empty input
    yields ``insufficient``.
    """
    set_a = part_values(a)
    set_b = part_values(b)
    if not set_a or not set_b:
        return "insufficient"
    if set_a == set_b:
        return "agree"
    if set_a.issubset(set_b) or set_b.issubset(set_a):
        return "consistent"
    return "conflict"


def part_values(tokens) -> set:
    """Normalize part-code tokens to a comparable set (numeric where possible)."""
    values = set()
    for token in tokens:
        value = code_value(token)
        values.add(value if value is not None else normalize(token))
    return values
