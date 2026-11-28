"""Catalog-aware filename and text-layer recognition (WP-19).

Builds a bounded rule set from the editable catalog (works, work aliases,
instrument variants, playable parts, instrument aliases), compares filename
and PDF text-layer evidence, and persists the outcome as immutable
``RecognitionCandidate``/``CandidatePart`` rows plus the file's independent
``candidate_state``. Recognition never approves: no proposal, inspection,
assignment or availability is changed here. Unresolved scanned files stay
pending visual review (WP-20a).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import PurePosixPath

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.archive import models as m
from apps.catalog.models import Arrangement, InstrumentAlias, InstrumentVariant, Part, Work, WorkAlias
from core import recognition as rec

#: Bounded rule-set caps; the local catalog is small, these fail closed.
MAX_ROWS = 20_000
#: Maximum text lines inspected per document (heading region heuristic).
MAX_TEXT_LINES = 20
#: Excerpt bound matching RecognitionCandidate.excerpt.
MAX_EXCERPT = 4096

WORK_AMBIGUOUS = "ambiguous"


@dataclass(frozen=True)
class RuleSet:
    version: str
    works: dict = field(default_factory=dict)  # title_key -> [work ids]
    work_aliases: dict = field(default_factory=dict)  # alias_key -> work id
    variants: tuple = ()  # dicts: id, name_key, pitch_key
    parts_by_instrument: dict = field(default_factory=dict)  # variant id -> [part dicts]
    part_instrument: dict = field(default_factory=dict)  # part id -> variant id
    part_by_alias: dict = field(default_factory=dict)  # alias_key -> part id
    instrument_by_alias: dict = field(default_factory=dict)  # alias_key -> variant id


def build_rule_set(using="default") -> RuleSet:
    """Snapshot the active catalog into a bounded, versioned rule set."""
    works: dict = {}
    for key, identifier in Work.objects.using(using).filter(active=True).values_list("title_key", "id")[:MAX_ROWS]:
        works.setdefault(key, []).append(identifier)
    work_aliases = {
        alias_key: work_id
        for alias_key, work_id in WorkAlias.objects.using(using)
        .filter(active=True)
        .values_list("alias_key", "work_id")[:MAX_ROWS]
    }
    variants = tuple(
        {"id": identifier, "name_key": name_key, "pitch_key": rec.canonical_pitch(transposition)}
        for identifier, name_key, transposition in InstrumentVariant.objects.using(using)
        .filter(active=True)
        .values_list("id", "name_key", "transposition")[:MAX_ROWS]
    )
    parts_by_instrument: dict = {}
    part_instrument: dict = {}
    for identifier, instrument_id, code in (
        Part.objects.using(using)
        .filter(active=True, instrument__active=True)
        .values_list("id", "instrument_id", "code")[:MAX_ROWS]
    ):
        parts_by_instrument.setdefault(instrument_id, []).append(
            {"id": identifier, "code": code, "code_key": rec.normalize(code)}
        )
        part_instrument[identifier] = instrument_id
    alias_rows = list(
        InstrumentAlias.objects.using(using)
        .filter(active=True)
        .values_list("alias_key", "part_id", "instrument_id")[:MAX_ROWS]
    )
    part_by_alias = {key: part_id for key, part_id, _instrument in alias_rows if part_id is not None}
    instrument_by_alias = {key: instrument_id for key, _part, instrument_id in alias_rows if instrument_id is not None}
    snapshot = {
        "works": sorted((key, sorted(str(identifier) for identifier in ids)) for key, ids in works.items()),
        "work_aliases": sorted((key, str(identifier)) for key, identifier in work_aliases.items()),
        "variants": sorted((str(variant["id"]), variant["name_key"], variant["pitch_key"]) for variant in variants),
        "parts": sorted((str(part["id"]), part["code"]) for group in parts_by_instrument.values() for part in group),
        "part_instruments": sorted(
            (str(part_id), str(instrument_id)) for part_id, instrument_id in part_instrument.items()
        ),
        "part_aliases": sorted((key, str(identifier)) for key, identifier in part_by_alias.items()),
        "instrument_aliases": sorted((key, str(identifier)) for key, identifier in instrument_by_alias.items()),
    }
    digest = hashlib.sha256(json.dumps(snapshot, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    return RuleSet(
        version=f"wp19-{rec.RULE_VERSION}-{digest[:16]}",
        works=works,
        work_aliases=work_aliases,
        variants=variants,
        parts_by_instrument=parts_by_instrument,
        part_instrument=part_instrument,
        part_by_alias=part_by_alias,
        instrument_by_alias=instrument_by_alias,
    )


def _variant_matches(parsed, rules) -> list:
    """All variants whose normalized name matches the parsed label name."""
    if not parsed.name:
        return []
    return [variant for variant in rules.variants if variant["name_key"] == parsed.name]


def match_instrument(label, rules):
    """Match a raw instrument label against the rule set.

    Returns ``(variant_ids, part_ids, exact)``. Ambiguous names yield several
    variant ids; part ids come from resolved part-code segments and part
    aliases. The caller records conflicts, never silently narrows.
    """
    key = rec.normalize(label)
    if not key:
        return [], [], False
    if key in rules.part_by_alias:
        part_id = rules.part_by_alias[key]
        variant_id = rules.part_instrument.get(part_id)
        return ([variant_id] if variant_id else []), [part_id], True
    if key in rules.instrument_by_alias:
        variant_id = rules.instrument_by_alias[key]
        parts = _parts_for(rec.parse_label(label), [variant_id], rules)
        return [variant_id], parts, True
    parsed = rec.parse_label(label)
    variants = _variant_matches(parsed, rules)
    if not variants:
        return [], [], False
    if parsed.pitch:
        pitch = rec.canonical_pitch(parsed.pitch)
        variants = [variant for variant in variants if variant["pitch_key"] == pitch]
    exact = bool(parsed.pitch)
    parts = _parts_for(parsed, [variant["id"] for variant in variants], rules)
    return [variant["id"] for variant in variants], parts, exact


def _parts_for(parsed, variant_ids, rules) -> list:
    if not parsed.part_tokens or not variant_ids:
        return []
    resolved: list = []
    for token in parsed.part_tokens:
        key = rec.normalize(token)
        if key in rules.part_by_alias:
            if rules.part_by_alias[key] not in resolved:
                resolved.append(rules.part_by_alias[key])
            continue
        for variant_id in variant_ids:
            for part in rules.parts_by_instrument.get(variant_id, ()):  # noqa: SIM118
                if rec.codes_match(token, part["code"]) and part["id"] not in resolved:
                    resolved.append(part["id"])
    return resolved


def match_work(title, rules):
    """Match a title string. Returns ``(work_id | None | WORK_AMBIGUOUS, exact)``."""
    key = rec.normalize(title)
    if not key:
        return None, False
    if key in rules.works:
        if len(rules.works[key]) > 1:
            return WORK_AMBIGUOUS, False
        return rules.works[key][0], True
    if key in rules.work_aliases:
        return rules.work_aliases[key], True
    # Bounded prefix relations in both directions; anything else is unknown.
    longer = [work_id for work_key, ids in rules.works.items() if work_key.startswith(key + " ") for work_id in ids]
    if len(longer) == 1:
        return longer[0], False
    if len(longer) > 1:
        return WORK_AMBIGUOUS, False
    shorter = [work_id for work_key, ids in rules.works.items() if key.startswith(work_key + " ") for work_id in ids]
    if len(shorter) == 1:
        return shorter[0], False
    if len(shorter) > 1:
        return WORK_AMBIGUOUS, False
    return None, False


def _stem_words(stem) -> list:
    """Tokenize a filename stem without breaking internal code separators.

    Separator characters (``-``, ``|``, ``_``) at a token's edges end the
    token; a hyphen inside a token keeps combined codes like ``1-2`` intact.
    """
    words = []
    for word in str(stem).split():
        word = word.strip("-–—|_")
        if word:
            words.append(word)
    return words


def _filename_evidence(stem, rules):
    """Classify a filename stem into instrument and title evidence.

    The instrument is the longest word suffix that resolves against the rule
    set; the remaining leading words form the title. This covers both
    structured names ("Einzug - Klarinette A 2") and unseparated ones
    ("An der Nordseekueste Posaune1").
    """
    words = _stem_words(stem)
    instrument_id, instrument_ids, instrument_exact, parts, part_codes = None, [], False, [], []
    instrument_conflict = False
    title = stem
    for index in range(len(words)):
        candidate = " ".join(words[index:])
        variant_ids, part_ids, exact = match_instrument(candidate, rules)
        if not variant_ids and not part_ids:
            continue
        part_codes = list(rec.parse_label(candidate).part_tokens)
        if len(variant_ids) == 1:
            instrument_id, instrument_ids, instrument_exact, parts = (
                variant_ids[0],
                variant_ids,
                exact,
                list(part_ids),
            )
        elif len(variant_ids) > 1:
            instrument_ids, instrument_conflict = variant_ids, True
            parts = list(part_ids)
        else:
            # A bare part-alias without an instrument: record parts only.
            parts = list(part_ids)
        title = " ".join(words[:index])
        break
    work_id, work_exact = match_work(title, rules) if title else (None, False)
    return {
        "stem": stem,
        "title": title,
        "work_id": None if work_id == WORK_AMBIGUOUS else work_id,
        "work_exact": work_exact,
        "work_conflict": work_id == WORK_AMBIGUOUS,
        "instrument_id": instrument_id,
        "instrument_ids": instrument_ids,
        "instrument_exact": instrument_exact,
        "instrument_conflict": instrument_conflict,
        "parts": parts,
        "part_codes": part_codes,
    }


def _text_evidence(lines, rules, filename):
    """Classify extracted text lines into instrument, part and title evidence.

    Only bounded heading-region heuristics run here; nothing OCR-like. A line
    that resolves to a known instrument contributes its instrument and parts;
    a bare part-code line (header pages often print only "2/3") extends the
    filename's instrument. Conflicting instruments are recorded, never merged.
    """
    instrument_id = filename["instrument_id"]
    observed: list = []
    parts: list = []
    part_codes: list = []
    title_candidate: str | None = None
    for raw in lines[:MAX_TEXT_LINES]:
        line = str(raw).strip()
        if not line:
            continue
        parsed = rec.parse_label(line)
        variant_ids, part_ids, _exact = match_instrument(line, rules)
        if variant_ids:
            if len(variant_ids) == 1:
                variant_id = variant_ids[0]
                if instrument_id is None:
                    instrument_id = variant_id
                elif variant_id != instrument_id:
                    observed.append(variant_id)
                if variant_id == instrument_id:
                    part_codes.extend(parsed.part_tokens)
                    if part_ids:
                        parts = list(dict.fromkeys(parts + part_ids))
            else:
                observed.extend(variant_ids)
            continue
        if parsed.has_part and instrument_id is not None:
            part_codes.extend(parsed.part_tokens)
            parts = list(dict.fromkeys(parts + _parts_for(parsed, [instrument_id], rules)))
            continue
        if title_candidate is None and 4 <= len(line) <= 80 and sum(ch.isalpha() for ch in line) >= 3:
            title_candidate = line
    instrument_conflict = len({value for value in (instrument_id, *observed) if value}) > 1
    work_id, work_exact = (None, False)
    if title_candidate:
        work_id, work_exact = match_work(title_candidate, rules)
    return {
        "title": title_candidate or "",
        "work_id": None if work_id == WORK_AMBIGUOUS else work_id,
        "work_exact": work_exact,
        "work_conflict": work_id == WORK_AMBIGUOUS,
        "instrument_id": instrument_id,
        "instrument_conflict": instrument_conflict,
        "parts": parts,
        "part_codes": part_codes,
    }


def _verdict(filename, text, rules):
    """Combine both sources into PROPOSED / CONFLICT / UNKNOWN with evidence."""
    reasons: list = []
    conflict = False
    work_id = filename["work_id"] or text["work_id"]
    if filename["work_conflict"] or text["work_conflict"]:
        conflict = True
        reasons.append("work_ambiguous")
    if filename["work_id"] and text["work_id"] and filename["work_id"] != text["work_id"]:
        conflict = True
        reasons.append("work_conflict_between_sources")
    if not work_id:
        reasons.append("work_unresolved")
    instrument_id = filename["instrument_id"] or text["instrument_id"]
    if filename["instrument_conflict"] or text["instrument_conflict"]:
        conflict = True
        reasons.append("instrument_ambiguous")
    if filename["instrument_id"] and text["instrument_id"] and filename["instrument_id"] != text["instrument_id"]:
        conflict = True
        reasons.append("instrument_conflict_between_sources")
    if not instrument_id:
        reasons.append("instrument_unresolved")
    same_instrument = filename["instrument_id"] == text["instrument_id"] or (
        not filename["instrument_id"] or not text["instrument_id"]
    )
    if filename["part_codes"] and text["part_codes"] and same_instrument:
        relation = rec.parts_agree(filename["part_codes"], text["part_codes"])
        if relation == "conflict":
            conflict = True
            reasons.append("part_conflict_between_sources")
    parts: list = []
    if not conflict:
        for source in (filename, text):
            for part_id in source["parts"]:
                if part_id not in parts:
                    parts.append(part_id)
    if conflict:
        state = m.ArchiveFile.CandidateState.CONFLICT
        confidence = None
    elif work_id or parts:
        state = m.ArchiveFile.CandidateState.PROPOSED
        confidence = _confidence(filename, text, work_id, instrument_id, parts)
    else:
        state = m.ArchiveFile.CandidateState.UNKNOWN
        confidence = None
    reasons.append("sources:filename+text" if (text["title"] or text["instrument_id"]) else "sources:filename")
    return state, reasons, confidence, work_id, instrument_id, parts


def _confidence(filename, text, work_id, instrument_id, parts) -> float:
    scores = []
    if work_id:
        scores.append(0.6 if (filename["work_exact"] or text["work_exact"]) else 0.5)
    if instrument_id:
        scores.append(0.6 if (filename["instrument_exact"] or text.get("instrument_exact")) else 0.5)
    if parts:
        scores.append(0.6)
    if not scores:
        return 0.2
    base = sum(scores) / len(scores)
    both_sources = bool(filename["work_id"] and text["work_id"])
    return round(min(0.95, base + (0.1 if both_sources else 0.0)), 2)


def _arrangement_for(work_id, using):
    found = list(
        Arrangement.objects.using(using)
        .filter(work_id=work_id, active=True, work__active=True)
        .values_list("pk", flat=True)
    )
    return found[0] if len(found) == 1 else None


def _excerpt(filename, text) -> str:
    pieces = []
    if filename["stem"]:
        pieces.append("Dateiname: " + filename["stem"])
    if text["title"]:
        pieces.append("Text: " + text["title"])
    if filename["title"] and filename["title"] != text["title"]:
        pieces.append("Dateiname-Titel: " + filename["title"])
    return "\n".join(pieces)[:MAX_EXCERPT]


def ocr_lines(words):
    """Preserve printed line grouping rather than treating each word as a title."""
    lines = []
    for word in words:
        line_identity = word.get("line")
        new_line = not lines
        if lines:
            if line_identity is not None or lines[-1][2] is not None:
                new_line = line_identity != lines[-1][2]
            else:
                new_line = abs(lines[-1][0] - word["box"][1]) > max(3, (word["box"][3] - word["box"][1]) // 2)
        if new_line:
            lines.append([word["box"][1], word["text"], line_identity])
        else:
            lines[-1][1] += " " + word["text"]
    return [line[1] for line in lines]


def record_candidate(version_id, *, filename, text_lines=(), using="default", ocr_evidence=None):
    """Analyze one verified source version and record immutable evidence.

    ``text_lines`` are extracted PDF text lines (empty for a text-less scan).
    Re-analysis under the same rule set is idempotent; a rule change keeps the
    old candidate and records a new one. This never approves or reassigns.
    """
    text_lines = tuple(str(line) for line in text_lines)[:MAX_TEXT_LINES]
    method = "TEXT_LAYER" if any(line.strip() for line in text_lines) else "FILENAME"
    if ocr_evidence is not None:
        method = "OCR"
    with transaction.atomic(using=using):
        if not m.SourceVersion.objects.using(using).filter(pk=version_id).exists():
            raise ValidationError("Source version does not exist.")
        version = m.SourceVersion.objects.using(using).get(pk=version_id)
        rules = build_rule_set(using)
        if ocr_evidence is not None and ocr_evidence.evidence["rules"] != rules.version:
            raise ValidationError("Recognition rules changed during OCR; reanalysis is required.")
        rule_version = ocr_evidence.cache_key if ocr_evidence is not None else rules.version
        existing = (
            m.RecognitionCandidate.objects.using(using)
            .filter(source_version=version, method=method, input_sha256=version.sha256, rule_version=rule_version)
            .first()
        )
        if existing is not None:
            return existing, list(existing.parts.using(using).all())
        stem = PurePosixPath(str(filename)).stem
        filename_evidence = _filename_evidence(stem, rules)
        text_evidence = _text_evidence(text_lines, rules, filename_evidence)
        state, reasons, confidence, work_id, instrument_id, parts = _verdict(filename_evidence, text_evidence, rules)
        if ocr_evidence is not None:
            # Keep a misleading or partial PDF text layer as independent evidence,
            # not a reason to skip OCR or silently override its observations.
            layer_lines = ocr_evidence.evidence["text_layer"].splitlines()[:MAX_TEXT_LINES]
            layer = _text_evidence(layer_lines, rules, filename_evidence)
            layer_state, layer_reasons, _, layer_work, layer_instrument, layer_parts = _verdict(
                filename_evidence, layer, rules
            )
            conflict_reasons = []
            if text_evidence["work_id"] and layer["work_id"] and text_evidence["work_id"] != layer["work_id"]:
                conflict_reasons.append("work_conflict_ocr_text_layer")
            if (
                text_evidence["instrument_id"]
                and layer["instrument_id"]
                and text_evidence["instrument_id"] != layer["instrument_id"]
            ):
                conflict_reasons.append("instrument_conflict_ocr_text_layer")
            if (
                text_evidence["part_codes"]
                and layer["part_codes"]
                and rec.parts_agree(text_evidence["part_codes"], layer["part_codes"]) == "conflict"
            ):
                conflict_reasons.append("part_conflict_ocr_text_layer")
            if layer_state == m.ArchiveFile.CandidateState.CONFLICT:
                conflict_reasons.extend(reason for reason in layer_reasons if not reason.startswith("sources:"))
            if conflict_reasons:
                state, confidence, parts = m.ArchiveFile.CandidateState.CONFLICT, None, []
                reasons.extend(conflict_reasons)
            elif state != m.ArchiveFile.CandidateState.CONFLICT:
                work_id = work_id or layer_work
                instrument_id = instrument_id or layer_instrument
                parts = list(dict.fromkeys(parts + layer_parts))
                if work_id or parts:
                    state = m.ArchiveFile.CandidateState.PROPOSED
            if layer_lines:
                reasons.append("sources:pdf_text_layer")
            reasons = list(dict.fromkeys(reasons))
        arrangement_id = _arrangement_for(work_id, using) if work_id else None
        region = {}
        excerpt = _excerpt(filename_evidence, text_evidence)
        if ocr_evidence is not None:
            if ocr_evidence.source_version_id != version.pk:
                raise ValidationError("OCR evidence source mismatch.")
            evidence = ocr_evidence.evidence
            region = {"page": evidence["page"], "box": evidence.get("display_box", [0, 0, 1, 1]), "unit": "NORMALIZED"}
            excerpt = (excerpt + "\nOCR: " + "\n".join(text_lines) + "\nPDF: " + evidence["text_layer"])[:MAX_EXCERPT]
            reasons.append("sources:local_ocr")
        file = m.ArchiveFile.objects.using(using).filter(source_version=version, kind="BASE").first()
        candidate = m.RecognitionCandidate.objects.using(using).create(
            source_version=version,
            archive_file=file,
            input_sha256=version.sha256,
            method=method,
            excerpt=excerpt,
            region=region,
            proposed_work_id=work_id,
            proposed_arrangement_id=arrangement_id,
            confidence=confidence,
            rule_version=rule_version,
            reasons=reasons,
        )
        candidate_parts = [
            m.CandidatePart.objects.using(using).create(candidate=candidate, part_id=part_id) for part_id in parts
        ]
        candidate.sealed = True
        candidate.save(using=using)
        if file is not None:
            file.candidate_state = state
            file.save(using=using, update_fields=["candidate_state"])
        return candidate, candidate_parts
