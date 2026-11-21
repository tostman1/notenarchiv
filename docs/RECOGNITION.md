# Filename and text-layer recognition (WP-19)

This package implements the recognition engine for AR-08 to AR-11. It is
evidence and comparison only: recognition records immutable candidates and the
file's independent `candidate_state`. It never approves, never proposes
directly into the review workflow, and never reassigns or replaces an existing
approval. Scanned files without a usable text layer stay `UNKNOWN`/`CONFLICT`
and remain pending explicit visual review (WP-20a). OCR is a later package
(WP-25) and is not part of this engine.

## Layers

- `core.recognition` — pure, Django-free primitives: NFKC/whitespace/casefold
  normalization, German and English pitch classes, bounded roman numerals,
  combined part-code splitting (`II/III`, `1-2`, `2_3`), label parsing
  (instrument name, optional pitch, optional part code), numeric-or-roman part
  comparison and the `agree` / `consistent` / `conflict` / `insufficient`
  relation used to compare sources.
- `apps.archive.recognition` — catalog-aware engine and services.

The pure layer holds no catalog data; the Django layer snapshots the active
catalog into a bounded `RuleSet` per analysis and records its content hash as
the candidate `rule_version` (plus a fixed built-in grammar version).

## Evidence sources

`record_candidate(version_id, filename=..., text_lines=...)` analyzes one
verified `SourceVersion`:

1. **Filename evidence** — the stem is tokenized (separator characters at a
   token edge; internal `-` keeps combined codes such as `1-2` intact). The
   longest word suffix that resolves against the rule set is the instrument
   and part; the remaining leading words are the title.
2. **Text-layer evidence** — bounded heading-region heuristics over extracted
   lines (at most 20 lines, no OCR). A line that resolves to a known
   instrument contributes it; a bare part-code line (header pages often print
   only `2/3`) extends the filename's instrument. The first plausible title
   line is compared against the rule set.

Both sources always run; a text-less scan is a filename-only candidate.

## Rule set and matching

- Works and work aliases match by normalized exact key, then by a single
  unambiguous bounded prefix relation in either direction. Multiple candidates
  are `ambiguous`, never silently narrowed.
- Instrument variants match by normalized name plus, when present, the pitch
  token (so `Klarinette A` and `Klarinette Bb` are distinct). Instrument
  aliases (instrument or single part target) take precedence and are exact.
- Part codes match numerically or by normalized string, so `II` equals `2`.
  Combined codes keep every part of the PDF (AR-10: `Trombone II/III` is one
  PDF assigned to both parts; no splitting).
- Editable aliases and rules are the catalog rows themselves
  (`WorkAlias`, `InstrumentAlias`, variants, parts); all are versioned into
  the candidate `rule_version` with their active flags.

## Verdict

`PROPOSED` / `CONFLICT` / `UNKNOWN` (`ArchiveFile.CandidateState`):

- A **conflict** is recorded when either source is ambiguous, when the two
  sources name different works or different instruments, or when both sources
  assert part codes that do not agree. A subset relation (a filename
  `1-2` with a page header printing `2`) is consistent, not a conflict.
  Conflicting candidates carry no part selection.
- A **proposal** requires a resolved work or parts; confidence is bounded to
  `[0, 1]` and reflects exactness plus both-source agreement. Confidence 1
  alone cannot approve anything (AR-11).
- **Unknown** means the evidence is insufficient; the file stays in the
  pending visual-review area.

Disagreement between filename and content is always surfaced as a prominent
conflict (AR-11); agreement yields a plausible proposal; missing/illegible
evidence is uncertain.

## Immutability and idempotence

- Candidates and their parts are immutable; a rule change or re-analysis
  records a **new** sealed candidate and keeps the history (AR-11 rule
  versions and provenance).
- Re-analysis of the same version under the same rule set is idempotent and
  returns the existing candidate.
- `candidate_state` is the only field recognition mutates on `ArchiveFile`;
  review, publication and assignment states are untouched.

## Verification

Synthetic tests cover the plan acceptance cases: exact/alias/unknown work
matches, pitch disambiguation, roman numerals, combined parts (`1-2`,
`II-III`), Unicode normalization, Posaune-1 vs Posaune-2 conflicts,
ambiguous-instrument conflicts, rule-version change history, idempotence,
candidate immutability and the explicit no-approval invariant. No OCR, no
files, no network and no external data are used.
