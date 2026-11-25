# Development handoff — OpenCode to Codex

Date: 2026-11-25. This is the latest transfer snapshot, not a new product design.
Git and the binding repository documents are authoritative; no chat is required.

## Transfer target and authorization

- Repository: `tostman1/notenarchiv`; remote: `https://github.com/tostman1/notenarchiv.git`.
- Transfer branch: `fix/ci-waiter-p0`; PR [#55](https://github.com/tostman1/notenarchiv/pull/55), open, targeting `main`.
- Comparison base / current verified main: `0d24dae03711254e48a0c167c36ff44a74de4600`.
- P0 implementation commit: `fa675797c2f310ce476deaf4d3aebb402d23b585`.
- The reported older baseline `3dc3eb4e5cde0e3ed6761564ceefb29e956693f2`
  integrated PR #53; Main CI `45512749289` succeeded at that exact SHA.
  Since then PR #54 integrated release-evidence documentation at the comparison
  base; Main CI `45574328173` succeeded at that exact SHA. No application change
  occurred between those two main checkpoints.
- P0 is implemented on the feature branch, **not merged**. Its owner instruction
  requires separate explicit merge authorization; this handoff does not supply it.
  No P1/P2, new product package, release, deployment, NAS access or branch deletion
  is authorized. Preserve existing branches and work.
- The final pushed branch HEAD must have subject exactly
  `chore(handoff): prepare agent transfer` and trailer `Handoff-Ready: yes`.
  Its SHA is obtained from GitHub, not a self-referential hash in this file.
  Any later commit invalidates that marker until another transfer commit exists.
  Final-marker CI is separate: use the exact-HEAD PR checks recorded on GitHub;
  never infer it from the implementation CI below.

## Repository reconstruction map

Read `AGENTS.md`, `REQUIREMENTS.md` (binding stable IDs), `ARCHITECTURE.md`
(target/invariants), `DECISIONS.md` (DEC-01–11, defaults D-01–15, evidence V-01–08),
`IMPLEMENTATION_PLAN.md` (package scope/dependencies/acceptance), then
`docs/PROCESS.md` and `docs/standard-checks.md` (canonical development/check gates).
`docs/PROGRESS.md` contains dated evidence/history; its current summary supersedes
older interim status rows. `docs/DEVELOPMENT_SEQUENCE.md` contains historical
counts/authorizations, not permission to restart old packages. README's older
preview feature list is not a current capability inventory: use
`config/features.py`, its tests, this snapshot and the integrated source instead.

Actual structure: `config/` settings, URLs and capability inventory; `apps/`
accounts/catalog/members/archive/projects/exports/printing/jobs; domain services
under those apps; pure PDF processing in `core/pdf/`; local templates/static
assets; migrations and synthetic tests; `scripts/`; `.github/workflows/`;
`Dockerfile`, Compose and `deploy/synology-test/`. Presence of an app, route stub
or target library in architecture is not evidence that its feature is complete.

Domain contracts: `docs/JOB_FRAMEWORK.md`, `ARCHIVE_MODEL.md`, `FILE_PUBLICATION.md`,
`INDEXING.md`, `RECOGNITION.md`, `PDF_CORE.md`, `PDF_PREVIEW.md`, `CATALOG.md`,
`EDITIONS.md`, `PROJECTS.md`, `PIECE_LIST.md`, `PARTICIPANTS.md`, `ENSEMBLE.md`,
`RULES.md`, `RESOLUTION.md`, `MATRIX.md`, `MATRIX_EDITS.md`, `MATRIX_BATCH.md`,
`PREFLIGHT.md`, `GENERATION_SNAPSHOTS.md`, `PDF_COMPOSITION.md`,
`PERSONAL_GENERATION.md`, `PROJECT_EXPORTS.md`, `PRINT_LAYOUT.md`, `PRINT_PDF.md`
and `EXPORT_LIBRARY.md`. Test links/requirement coverage: `tests/TRACEABILITY.md`.
German archivist manuals are in `docs/`; German test-install guide is
`deploy/synology-test/README.de.md`.

## Implemented / software verified / integrated

- Foundation/auth/local shell/diagnostics and durable singleton jobs: WP-01–05c;
  hardened mount/config, CI and release infrastructure: WP-08/09/10.
- Catalog/members and manual archive: WP-11–21, WP-23a/b (including WP-20a/b;
  excluding physical NAS WP-22 and OCR WP-24 onward). Real hash-verified CLEAN publication, read-only RAW,
  separate STATUS, bounded PDF inspection, filename/text-layer candidates, local
  preview, individual inspected approval, explicitly inspected batch confirmation,
  library/completeness, edition preferences and authorized original/ZIP downloads.
- Projects/participants/reserves/ensemble rules/one resolver/matrix: WP-29–35
  including WP-33a–d; preflight/immutable snapshots WP-36a/b; personal reading,
  excerpt/contents and regular print PDFs WP-37a–c/38a/b; unified historical export
  library/targeted regeneration WP-39. PR #50 integrated WP-39 at
  `fd0ed9ce0b4efeb05c7210f237dcb7896c38a31a`.
- WP-47a software consistent backup/isolated restore is integrated (PR #27).
  WP-06/07 now include the verified synthetic current-feature web/worker/private
  TLS stack through PR #51. This is not physical NAS acceptance or completed
  full-product operations WP-48/49/52/53.
- Current-feature distribution PR #51 and packaging recovery PR #52 are complete;
  source/test-only release evidence is in `docs/RELEASES.md`. Source through WP-39
  passed 956 Linux tests/26 browsers and hardened stack/security gates. Published
  `v0.1.0-test.1` source is `4ccd2698204a1e69ec7c1c4f128acf8e6c65d809`, **not**
  current main or P0. Image digest:
  `sha256:f628501dbc3fbe65c4e53bb2ab6c4723bd4014bca582656383ffd528df543e5a`.
  Recovery `45434860531` promoted/reused verified bytes and completed install
  assets; no rebuild/overwrite. Historical `v0.1.0-preview.1` remains unchanged.

## Governance and P0 delivery

PR #53 consolidated governance: `docs/PROCESS.md`, SHA-bound deterministic
`scripts/wait_for_ci.py`, exact commands/contracts in `docs/standard-checks.md`,
and DEC-11. Main is unprotected; reviewed-green gating is manual. No model-driven
CI polling; one deterministic wait per exact-SHA phase, compact terminal evidence,
bounded duration/retries/rate-limit handling, no merge on missing/skipped/stale CI.

P0 reuses that waiter and `scripts/ci_changes.py`: Foundation and Container cannot
be removed by caller overrides. Container omission requires verified exact local
base/head Git classification limited to `docs/PROGRESS.md` and
`tests/TRACEABILITY.md`, plus successful `changes` evidence; unavailable evidence
requires full checks. Run mode always requires both individual jobs. Missing,
malformed/mismatched SHAs and incomplete/ambiguous API pages fail closed. Original
exit codes/compact JSON contract remain; initial delay is deadline-capped and
transient backoff is applied once. Product/workflow functionality was not changed.

Synthetic baseline reproduction: 11 failures / 6 passes; corrected focused suite
78 passes (`tests/test_wait_for_ci.py`, `test_ci_waiter_regressions.py`,
`test_ci_workflow.py`). Local full suite 902 passes / 131 Windows/POSIX skips;
browsers 22 passes / 4 POSIX skips. Ruff lint/format, lockfile, Django system and
migration drift checks passed. Earlier outer timeouts were not counted as success.
Qwen delegation was attempted but cancelled without edits; coordinator implemented
and reviewed P0 directly. Implementation-SHA CI was still pending at snapshot
preparation; no success is inferred. The documentation-only transfer supersedes
that PR head and requires its own exact-SHA CI. Its compact result is published
on PR #55; source tests above remain reusable because implementation is unchanged.

## Outstanding scope, limitations and decisions

- No new product implementation is in progress in this transfer. P0 integration
  is pending authorization and exact-head CI/review. Only PR #55 was open and
  no open GitHub issues or submitted reviews were reported at snapshot inspection;
  that is not proof that undiscovered defects do not exist.
- Planned: local OCR WP-24/25/26 and private quality WP-28; complete integrity/
  lifecycle WP-27; enhancement WP-40a/b/c/f and WP-41; actual marchbook layout
  WP-42 (basic configuration is partial, output unavailable); optional adapter
  WP-43; physical printer WP-44a/b/45/46; private NAS WP-22/47b/52/53 and remaining
  full operations/security/license WP-48/49/50/51. Existing filename/text evidence,
  safe reindex primitives or regular print PDFs do not complete these packages.
- RAW must remain host/mount read-only; never copy real notes/members/OCR/DB/secrets
  into Git, CI, logs or external AI. Every new/changed PDF still needs visual
  approval. No music numbering, silent substitutions, snapshot mutation or automatic
  retry after uncertain physical print submission. `DEBUG_MODE` never enables
  Django DEBUG or disables auth/CSRF/safe paths/non-root safeguards.
- Known technical boundaries: unsupported POSIX publication fails closed on Windows;
  kernel-blocked filesystem I/O cannot be given a universal hard deadline; STATUS
  is a two-file publication with JSON authoritative. Historical Windows queue/
  timing failures and concurrent-suite interference are recorded in PROGRESS;
  serial P0 suite passed. CI action Node deprecation warnings and redundant older
  status/README claims remain documentation/toolchain debt, not new authorized work.
- Outstanding DECISIONS V-01–08: DSM/ACL/mount identity and RAW negatives; real
  SQLite/WAL/load/recovery/resources; authorized local OCR/enhancement quality;
  printer endpoints/media/margins/status; backup destination/retention/full restore;
  unusual-format/cover/contents and retention choices; license/copyright and final
  dependency notices/registry/protection evidence. Existing synthetic CI and
  attestations must not be presented as these physical/product decisions.

## Environment and verification

Use Python 3.12, Django 5.2 LTS and `uv sync --locked`. Start the managed synthetic
local profile with `./dev.ps1 start` (manual auth optional); see
`docs/DEV_WORKFLOW.md`, `docs/DEVELOPMENT.md` and `docs/dev-workflow.de.md`.
`.dev/`, venvs, capability tokens, browser installs and result JSON are local-only
and are not transfer prerequisites: recreate them from pinned setup, never copy
the local DB. Browser checks need Node, `playwright-core@1.62.1`, NODE_PATH and
Chrome (or documented Edge channel). Local Windows used Node v24.22.3; portable
setup is documented, no machine-specific path belongs in application files.

Mandatory delivery gates are exactly `docs/standard-checks.md`: locked environment,
Ruff lint/format, full pytest, separate browser suite, Django system/migration
checks, and exact-SHA Foundation/Container Linux CI (runtime audit, native PDF,
actual hardened container/Compose/security/synthetic stack/restore). Windows skips
are not Linux acceptance. Docker was unavailable locally; Linux CI supplies that
software evidence. This handoff changes docs only; reuse valid implementation
tests rather than rerunning expensive local suites. HANDOFF.md is outside the
docs-only allowlist, so this PR's final marker requires **both** CI jobs.

Deployment requires separate owner authorization. Use the digest-pinned
`deploy/synology-test/compose.yaml` and German guide for synthetic test distribution,
not the obsolete preview image or generic source-example paths. Read
`docs/SYNOLOGY_TEST_RELEASE.md`, `INSTALL.md`, `RESTORE.md`, `UPDATE.md`,
`DEBUG_MODE.md` and `RELEASES.md`. No actual NAS deployment/real-data access was
performed. Physical acceptance and production release remain blocked separately.

## Exact next action and priorities

1. Apply AGENTS.md takeover readiness gate to **remote HEAD** of
   `fix/ci-waiter-p0` before checkout/edit/full review. Verify local status, fetch
   safely, exact subject/trailer and snapshot consistency. If invalid, stop.
2. Review **all** commits/diffs from comparison base `0d24dae03711254e48a0c167c36ff44a74de4600`,
   including P0 and this transfer. Inspect exact-HEAD CI and PR #55 review state;
   reconcile any newer main change without losing work. Obtain explicit P0 merge
   authorization before integration; if granted, enforce reviewed-green-head
   gates and one exact-merge-SHA Main CI wait. Do not merge merely to take over.
3. Recommend WP-24 bounded local OCR engine as the next software package **for
   owner approval**, followed by WP-25/26. Read plan WP-24, AR-08–11/OP-02 and
   PDF/container contracts: pinned local Tesseract/pytesseract/languages, bounded
   regions/resources/timeouts, synthetic noisy/skewed heading text/boxes, language
   failures, exact hash/profile/rule cache, no network, no named-scan OCR bypass,
   no automatic approval. Update lock/license/container CI and retain full gates.
   First verify WP-17/06 prerequisites. Private WP-22 synthetic NAS acceptance is
   a separate owner-authorized hardware priority before real use. P1/P2 and all
   product packages remain unstarted and unauthorized by this transfer.
