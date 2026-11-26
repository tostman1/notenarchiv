# Implemented acceptance traceability

GR-01/02, AR-01/02/09, OP-02/03/07:
`tests/test_publication_contract.py` checks platform-independent publication
policy rejects collisions, unsafe staging and read-only mutation before backend
effects, and requires retained identity before durable recovery acknowledgement.
Backend proof dispatch follows byte verification and precedes PDF inspection,
entry verification and durability; actual POSIX proof logic is exercised with
injected metadata for mismatched identities, unsafe types and link counts.
`tests/test_job_lifecycle.py` injects post-mutation publication failure into the
actual worker: persisted intent stays PENDING, acknowledgement/release remain
unreachable, proof is retained and uncertain work is not blindly retried.
These contracts supplement, not replace, physical publication/race tests and do
not establish a native Windows writable backend.

GR-01/02, AR-02/09, OP-03/07: `tests/test_stage_ownership.py` pins the exact POSIX
effective-UID comparison and archive/export cleanup dispatch before discard,
including owner and metadata failures. Mock consumer metadata has no POSIX UID;
this proves encapsulation, not native Windows ownership enforcement.

GR-01, OP-07: `tests/test_windows_security.py` checks current-process TOKEN_QUERY
access, non-inheritable handle cleanup, bounded token buffers, sanitized failures,
private SID representation and rejection of administrative/dangerous privilege
evidence. Native smoke is Windows-only. RAW isolation/publication remain false
even for acceptable token evidence; no ACL or process-role certification is implied.

GR-01, OP-07: `tests/test_windows_root_security.py` covers pinned-handle descriptor
queries, allocation release, bounded SID/ACL evidence, absent/null/empty DACLs,
private owner representation and fail-closed missing READ_CONTROL. Native synthetic
acceptance does not modify ACLs. Snapshot evidence always leaves RAW isolation and
publication uncertified; effective access and durable enforcement remain untested.
The source-reader suite also checks optional security-pin rights, strict boolean
selection, unchanged read-only stream access and initial pin cleanup. Native root
descriptor acceptance uses the public optional mode, not private handle replacement.

GR-01, OP-07: `tests/test_windows_access_security.py` checks pinned-root AccessCheck
evidence, query-only duplicate token access, bounded privilege buffers, mutation
masks including delete-child, owner comparison and deterministic resource cleanup.
Native acceptance queries only a synthetic directory. Root ACL snapshots do not
cover descendants, parent-entry deletion or all process roles; capabilities stay
uncertified even when effective root mutation rights are absent.

## Native read-only Windows source boundary

GR-01/02, AR-01/02/09, OP-02/03/07: `tests/test_source_reader.py` exercises actual
source traversal/hash/reread metadata on Windows and Linux. Windows cases use
real handles, hardlinks and reparses: unsafe leaves/parents and namespace aliases
are rejected; streams reject writes and conflicting opens/renames; ancestors are
pinned; a replaced child cannot redirect later reads; directory mutation aborts
inventory; root reentry and failed initialization cannot leak/lossily replace
owned handles. A known 100-ns timestamp and real hardlink identity provide
independent metadata oracles. Missing roots/writable backends cause no writes.
Additional real junction cases verify reparse leaves/ancestors and replaced-child
redirection without requiring symlink creation privilege; symlink cases remain.
The adapter is explicitly local NTFS/read-only. These tests do not prove global
RAW ACL denial, native publication/recovery, network shares or desktop packaging.
Existing actual POSIX indexing/publication/generation/backup suites remain gates.

## Shared managed-runtime proof

OP-07, GR-13, OP-02/03: `tests/test_portable_runtime.py` executes the synthetic
tool in a fresh process with a 60-second timeout and a foreign working directory.
It proves that inherited NAS/data/root/bind/diagnostics/print settings cannot
redirect the fixture into a protected sentinel installation. The tool exercises
actual Django migrations, single-instance exclusion, HTTP login/auth/CSRF,
worker ownership/shutdown/lock release and SQLite migration/user/lease data
parity after isolated restore (integrity and foreign-key checks included).
It emits only bounded fixed evidence. Existing production storage, publication,
worker recovery and backup/restore tests remain distinct; no native Windows
archive, installed desktop or physical acceptance is inferred.

## Portable filesystem consumers

`tests/test_backup_inventory_contract.py` exercises bounded traversal,
exclusions, directory replacement/mutation and unsafe metadata on both platforms.
`tests/test_marker_files.py` covers POSIX STATUS creation/known replacement,
foreign-content preservation and uncertain replacement errors without false
no-effect classification. `tests/test_root_directories.py` covers actual backend
identity, private-directory permissions, read-only denial and link rejection.
Existing indexing, publication, download and backup/restore suites remain gates.
The relative-path regression in `tests/test_settings.py` checks startup-pinned
local roots, database, secret and logs after a working-directory change.
These tests do not establish a native Windows writable backend or NAS acceptance.

## Portable runtime path initialization

`tests/test_settings.py` exercises nested/aliasing archive roots, database/secret/
log collisions, hardlinked runtime files and linked-root rejection before secret
or directory creation, fixed metadata errors and Windows namespace aliases.
With `tests/test_validate_config.py`, 53 targeted Windows
checks passed using real synthetic links under approved native access.
These are initialization checks, not evidence of native Windows publication,
desktop packaging or physical NAS safety acceptance.

## Revision-3 acceptance delta

The complete source-alias and reference-scenario matrix is
[REQUIREMENTS_CROSSWALK.md](../docs/REQUIREMENTS_CROSSWALK.md).
It maps all EXT-01–18, FUT-01–07 and REF-01–36 to canonical requirements,
WPs, explicit measurable oracles and bounded existing evidence.
Historical results below remain evidence for their original simple workflows.
New collection, source-region, segmentation, geometry, migration and duplex
criteria are planned unless individually verified. Similar test names do not
establish that coverage. Deferred criteria gate their later capability only.

Keep the existing PDF, archive, resolver, snapshot, project and export regression
suites. Extend them with multi-page/multi-work/multi-region fixtures and the
independent numerical/rendered oracles specified in the crosswalk. Validate
source/CLEAN hashes, stable identities, confirmation invalidation, old-schema
replay and isolated restore. Synthetic CI is distinct from private realistic
OCR quality, native Windows storage, packaged desktop and physical NAS/printer
acceptance. The current software baseline is verified Main CI 45640472935 at
`ca8647cfb04d26e3d61048e22e8885e6b5c460bb`.

Shared-runtime portability: `tests/test_pdf.py::test_vector_text_and_image_only_scan_are_distinct`
exercises the actual isolated PDF worker from a foreign working directory;
`tests/test_release.py::test_web_requires_initialized_database` verifies migration
checks select the installed entry point regardless of launcher directory.

Portable inventory boundary: `tests/test_inventory_contract.py` exercises
directory/file classification, fingerprints, limits, repeated identity and
changed-directory rejection without OS handles. `tests/test_inventory.py`
retains actual POSIX link/hash tests and checks mutation during enumeration.
The shared staging writer retains the archive copy and generated publication
suites. Direct POSIX regressions in `tests/test_archive_files.py` cover bounded
input, producer failure cleanup and no-clobber identity preservation.

## Development governance: deterministic CI waiting

DEC-08/DEC-11, GR-14, AGENTS.md, docs/PROCESS.md, docs/standard-checks.md:
`tests/test_wait_for_ci.py` verifies the `scripts/wait_for_ci.py` contract with a
mocked GitHub transport and a deterministic clock — exact-SHA binding, pending
polling at the bounded intervals, missing/required-check mismatch, foreign-SHA
and PR-head mismatch, failed and cancelled results, timeout, Retry-After
rate-limit waiting within and beyond the budget, unavailable after bounded
transient retries, run-mode 404 discovery, and CLI defaults. No real GitHub
workflow is triggered. Governance consolidation (AGENTS.md pointer, PROCESS.md,
standard-checks.md) keeps all review/approval/merge/release gates unchanged.

P0 hardening: `tests/test_ci_waiter_regressions.py` reproduces default/explicit
required-check bypass, missing/malformed SHA and aggregate-run false greens
(11 failures against the baseline). It verifies full required jobs in both modes,
the exact-diff cached docs-only exception with successful classification,
malformed/incomplete/ambiguous evidence, and individual run-job conclusions.
Combined targeted suite: 78 passed locally, including capped initial delay and
single transient-backoff regressions. Synthetic fixtures only; no product
functionality or CI/review/authorization gate changed. Final delivery CI is
reported on the PR; merge requires separate owner authorization.

## Current-feature Synology test acceptance — software verified

CI `45403811456` at `68f0fcf74c81f599a22bf46e1f8dc80de670c882` passed 956 Linux
tests/26 existing browsers and the actual NAS-profile Compose/TLS browser stack:

- OP-01/03/06, UI-01–03, GR-13/14: hardened web/worker/gateway, interactive setup,
  login/secure cookies/CSRF/host/HTTPS, local CSS/HTMX/PDF.js, disabled capabilities
  and direct-route denial, digest packaging, dependency/image/secret scans and SBOM.
- GR-01–06, AR-01–14: original demo indexing, independent STATUS, actual rendering
  of every PDF page, explicit inspection/correction/approval, real immutable CLEAN
  publication, RAW host/mount negatives, unchanged source bytes and isolated binds.
- PR-01–07, AS-01–08, EX-01/02/04/07–10, GR-07–12/15: participants/ensemble/matrix
  choice and reload, reserves/missing acknowledgment, shared personal reading and
  regular A4/A3 print PDFs, excerpts/contents, authenticated downloads, stale/targeted
  generation, immutable snapshots and exact source pins, retained prior artifacts.
- OP-02/05: actual worker process death after publication, automatic recovery,
  cancellation/partial failure without exposed complete batch, singleton/maintenance
  exclusion, restart/database/file persistence and existing full backup/restore smoke.

Drivers: `scripts/synology_stack_smoke.py`, `browser/synology_stack.cjs`,
`tests/synology_scenario.py`, `tests/test_synology_distribution.py`,
`tests/test_feature_availability.py`, `tests/test_review_ui.py` and
`tests/test_review_publication.py`. NAS hardware acceptance remains unverified.
Publication requires separate exact-source candidate and published-digest checks.

Publication software gate verified: original tag-source checks and image export
`45415635235`, complete published-digest stack and immutable candidate recovery
`45434860531`. PR #52 head/main `45421346339` / `45424991627` also passed the
release bash syntax regression. All seven distributed assets/hash metadata and
six bundle files checked against exact original source; the released Compose
pins the real GHCR digest and equals repository source. See docs/RELEASES.md for
exact source/digest/bundle hash and signed evidence. No physical NAS claim.

## WP-39 export library (verification in progress)

- EX-10/GR-15/AR-17: `test_export_library.py` verifies specific per-person part/edition/
  list/selection/catalog stale reasons, unaffected outputs, preserved historical bytes,
  actual file/input corruption distinctions, read-only classification and targeted scope.
- EX-03/09/OP-03: generated archive reading order/project-free exact pins/variant binding,
  fresh targeted print authorization, auth/CSRF/filter/project/download/ZIP isolation;
  existing direct archive download tests remain required.
- OP-02/EX-10: real Linux `test_export_library_publication.py` targeted one-person and
  archive reading publication/crash/replay preserve prior artifacts; browser library/
  targeted preflight/ZIP/archive download and hardened container acceptance required.

## WP-38b print renderer (verification in progress)

- EX-07/PT-01/02/GR-11/12: `test_print_pdf.py` exercises actual isolated 1-40-page
  layouts, exact A3/A4 media, both left/right vector visual fixtures, rotation/UserUnit,
  native A3/landscape/custom/crop, origins/generated boundaries and invalid inputs.
- GR-15/EX-09/OP-03: `test_print_authorization.py` checks exact copied source pins,
  separate snapshots, auth/CSRF/source-state/token/replay and project-free archive pins.
- OP-02/EX-10: `test_print_publication.py` executes real Linux full/excerpt/contents/
  archive no-clobber print effects with process death/restart/cancellation and retained
  reading bytes. `browser/test_print_exports.py` exercises actual local PDF.js and
  print download; hardened container smoke generates/verifies all print kinds.

## WP-38a regular print plan (verification in progress)

- GR-11/PT-01/02/EX-07: `test_print_layout.py` checks 1-6 and >6 arbitrary A4 runs,
  odd remainder, native A3, landscape/custom/crop, rotations/units/origins, media
  and transformed left/right corners; no cross-piece/position/document pairing.
- GR-12/15/OP-02: generated/reserve/missing boundaries, deterministic frozen input,
  explicit modes, invalid geometry/identity/options and bounded 1,000-page output.
  Pure planning has no original-file mutation, publication or printer interface.

## WP-37c project selections (verification in progress)

- EX-02/04/06, GR-07–10/12/15: `test_project_exports.py` covers exact one/multi-person
  excerpts, explicit editions/different parts, replacement at slot, original historical
  pins after removals/default changes, contents-only/reserves/missing and no list mutations.
- UI-01/03, OP-03, EX-08/09: same suite covers login/CSRF/stale/forged reports,
  foreign historical selections, incompatible/unconfirmed/corrupt inputs and missing ack.
- OP-02/GR-15: `test_excerpt_publication.py` runs real Linux excerpt/contents/historical
  no-clobber publication and crash recovery while preserving previous output bytes.
- `browser/test_project_exports.py` exercises actual current/historical/contents PDF
  downloads; `scripts/publication_smoke.py` verifies all kinds in hardened non-root,
  network-disabled containers. Windows physical skips must pass in Linux CI.
- `test_contents_download.py` verifies the participant-free applied receipt and
  authenticated download; `test_export_persistence.py` independently reopens SQLite
  contents and exact historical pins. Composition tests reject music inputs in
  contents-only mode and preserve German project metadata/reserve labels.

## WP-37b personal reading generation (verification in progress)

- EX-01/GR-07–10/EX-05/07/09: `test_personal_generation.py` checks pinned composition
  after project edits, exact distinct parts/editions with common contents/reserves,
  acknowledged placeholders and aggregate input bound; existing PDF composition/core
  tests cover original geometry, content streams, A3, rotation and active content.
- EX-09/GR-15/OP-02/03: `test_generation_downloads.py` checks exact applied receipt,
  immutable artifact trigger, safe names, login/GET-only, complete-state gating and
  missing/corrupt output denial. Snapshot authorization/persistence suites remain.
- OP-02/GR-15: `test_generation_publication.py` performs real Linux files/independent
  processes for stage/link/ack/completion deaths, restart, replay, multi-person failure,
  cancellation, missing/corrupt/foreign equal-hash stage evidence and private cleanup.
- UI-01/03/EX-01: `browser/test_personal_generation.py` and local-only Playwright
  exercise real preflight acknowledgement, worker and verified browser PDF download.
  Windows skips this physical route; Linux CI must pass it before integration.
- `scripts/publication_smoke.py` exercises actual hardened non-root network-disabled
  container generation/publication of two personal PDFs, hashes and ownership.

## Developer workflow / CI maintenance

- OP-03/GR-13/UI-01: `tests/test_dev_workflow.py` checks loopback local-only
  dedicated capability login, NAS/remote/forged rejection, restart account identity,
  manual authentication suite retained and diagnostic secret redaction.
- `tests/test_dev_server.py` exercises real startup/static/auto-login sessions,
  kill yes/no, Ctrl+C cleanup, repeated start/stop, stale state and unrelated port
  listener preservation. No process termination based on PID files/ports.
- OP-06: `tests/test_ci_workflow.py` and `ci_changes` tests preserve check names,
  full code/mixed/security/config verification, PR-only cancellation, main/reusable
  full scope; actionlint validates actual workflow. No NAS/production testing.

## WP-37a

- EX-05/GR-12/EX-07: `test_contents_reserve_placeholder_unicode_no_music_overlay`,
  `test_original_rotation_crop_userunit_and_vectors_preserved` compare exact music
  streams and native geometry, German contents/reserve/placeholder and Unicode.
- Optional cover/common contents pagination, independent excerpt pages/no pairing,
  unsupported glyph rejection, literal markup, generated dimensions/page limits
  in `tests/test_pdf_composition.py`; existing PDF security/annotation suite retained.
- Pure isolated builder only; no generation/download browser route or NAS acceptance.

## WP-36b

- GR-15/EX-09: `test_authorization_atomically_pins_and_enqueues`,
  `test_missing_ack_is_snapshot_bound_no_silent_skip`, `test_stale_token_and_full_subset_rejected`:
  exact report/acknowledgement and relational input pins, no stale/bypassed enqueue.
- Immutable project-edit survival, pinned withdrawal/deletion protection, raw SQL
  update guards, corrupt-file worker rejection, transaction rollback and forged
  payload cases in `tests/test_generation_snapshots.py`.
- `test_edit_between_verification_and_enqueue_rejected` checks the atomic second
  dependency read; `test_concurrent_authorization_replay_creates_one_job` uses
  independent file-backed SQLite connections and requires one shared run/job.
- `test_authorization_survives_independent_process_reopen` retains queued exact
  inputs despite later project edits. Worker-without-renderer and queued cancellation
  tests retain history and never imply successful output.
- Browser authorization rejects absent missing decisions, accepts exact reviewed
  report and replays without duplicate jobs. Existing preflight browser remains required.
- Artifact generation/publication/recovery is not implemented by WP-36b.

## WP-36a

- GR-09/EX-08: `test_report_identical_to_matrix_missing_ambiguous_and_reserve`,
  `test_missing_ack_requires_each_cell_and_no_generation_job`,
  `test_stale_selection_and_actor_tokens_rejected`: shared resolver parity,
  no unacknowledged missing selection, no inspection-to-generation bypass.
- EX-08/OP-03: corruption, parser failure, known unavailable input, pending
  conflicting candidate, auth/CSRF/subset/no-mutation cases in `test_preflight.py`.
- EX-08/EX-07: `test_layout_inspection_flags_native_a3_rotation_and_custom`;
  serial per-file inspection and report budgets are explicitly tested.
- `browser/test_preflight.py::test_preflight_browser` exercises German missing
  acknowledgements and blocking ambiguous/corrupted inputs with actual browser.
- Durable authorization and immutable generation snapshots are not yet implemented.

## WP-33d

- AS-02/UI-03: `test_filters_preserve_shared_list_and_absolute_numbers` covers
  name/participant/instrument and personal deviation selection without mutations;
  invalid filter parameters are rejected.
- AS-04/UI-03: `test_htmx_navigation_and_edits_retain_filters` covers bounded panel
  response and persisted filter state after revision-guarded default editing.
- AS-02/UI-03: `test_synthetic_100_by_50_bounded_render_queries` measures full HTML,
  SQL/time/size and enforces no per-cell SQL growth with identical source inputs.
- `browser/test_matrix_performance.py::test_large_matrix_browser` covers the 100 × 50
  paged project, last window, sticky header/column, exact filters, shared numbering
  and no-JavaScript reload. Existing cell/batch/stale-revision browsers remain required.
- No NAS performance or heterogeneous large-archive acceptance is implied.

This incremental register records WP-15 tests, not completion of future packages.
All fixtures are deterministic synthetic data. Physical tests require Linux;
Windows skips are not substitutes for their CI evidence.

| Requirement | WP-15 verification |
| --- | --- |
| GR-01, GR-02, AR-01, AR-02, AR-03 | `test_complete_new_import_verifies_copies_and_raw_is_identical`: independent byte-identical CLEAN copy, source hash/page metadata, no RAW markers and exact RAW inventory before/after |
| AR-04, OP-02 | Selection/payload tests; complete-import STATUS/progress assertions; actual process-death inventory/copy/STATUS recovery |
| AR-05, GR-06 | Changed/missing/corrupt history test; repeated hash idempotence and same-size/mtime change detection; failed traversal never infers missing |
| AR-06, GR-03, GR-04, AR-08 | Unknown pending CLEAN import with WP-19 evidence; no assignment, confirmation or usable files |
| AR-14, GR-05 | Separate folder partial-failure, source presence, validation, candidates, review and publication assertions; STATUS counts are not approval |
| OP-03 | Symlink/unknown STATUS conflict preservation, canonical selection and payload denial; existing WP-14 descriptor/fence and recovery suites remain required |

OCR, human review UI, NAS permissions/load and full integrity UI remain separately
scoped work packages; this register does not claim those gates were exercised.

## WP-16

- AR-04/UI-03: `tests/test_index_ui.py` verifies authenticated POST/CSRF selected/all
  queueing, bounded folder/review lists, worker/error visibility and exact JSON
  receipt/byte verification. Text-marker-only state cannot imply success.
- `browser/test_indexing.py` exercises real browser full/selected enqueue and
  cancellation; Linux continues through the real worker, verified STATUS and
  pending preview queue, with identical RAW and no inspection/usable assignment.

## WP-20a

- GR-03/04/05, AR-12/13/14: `tests/test_review_ui.py` covers read-only GET/preview,
  explicit version/proposal/hash/revision inspection, controlled combined parts,
  incompatible/inactive selection, personal attestation, rejection/new revision,
  corrupt bytes, failed publication and auth/CSRF. Metadata tests do not claim
  physical publication; existing WP-14 crash/recovery tests remain required.
- `browser/test_review.py` exercises actual PDF.js alongside candidate evidence,
  persistent correction/inspection and no preview auto-approval. Linux continues
  through real canonical queue/worker publication, confirmed combined assignments
  and unchanged RAW; existing WP-14 recovery protects the same publication path.

## WP-20b

- AR-13/GR-04: `tests/test_batch_review.py` verifies personal inspection, signed
  hash/version/proposal/revision/source state, stale/foreign/uninspected/changed
  selection rejection, POST/CSRF and entire-batch transaction rollback.
- `browser/test_batch_review.py` exercises real previous/next navigation, actual
  PDF inspection, persistent two-file selection and Linux durable batch publication
  with distinct no-clobber canonical destinations. Preview remains read-only.

## WP-21

- AR-15: `tests/test_library.py` verifies Unicode/casefold title and active alias
  interior matches, controlled arrangement/instrument/part/review/completeness
  filters, invalid filter/auth rejection, duplicate identities and pagination.
- AR-16/GR-05: independent required/optional/unknown expectation and confirmed/
  pending/missing material assertions; confirmed/withdrawn/missing/corrupt versions
  never become interchangeable, unreviewed candidates never usable; current manual
  correction takes precedence over historical recognition suggestions.
- `browser/test_library.py` exercises local-only live substring search, confirmed
  hash-verified edition, unknown completeness, independent expectation-template
  application and persisted incomplete/missing-part overview. No preferred edition,
  OCR, project generation or real NAS acceptance is claimed.

## WP-47a (software verified; private NAS acceptance separate)

- OP-05: `tests/test_backup.py` uses migrated independent synthetic installations,
  actual worker copy/combined approval, rollback-journal/WAL Backup API, physical
  CLEAN/PROCESSED/STATUS/config/secret/DATA and protected assignment restoration.
  Service locks, competing writers, missing/corrupt/extra/manifest-only bundles,
  symlinks, live-root overlap, bounds and independent RAW mismatch are negative gates.
- `scripts/publication_smoke.py` extends the actual hardened non-root/no-network
  image test with full bundle capture, isolated physical restore and reopened
  confirmed ORM assignments/verified PDF bytes. CLI tests cover actual commands
  and sanitized failures. Full Linux CI `45009366615` on `66926f9` passed (558
  tests, nine browsers and complete image/restore/security checks). Windows
  fail-closed skips are not NAS acceptance; no private installation data used.

## WP-23a (merged, software verified)

- AR-17/AS-05: `tests/test_editions.py` covers exact compatible arrangement/part,
  multiple versions, ambiguity/sole/preferred/explicit provenance, preference reset,
  transposition/clef incompatibility, pending/withdrawn/corrupt/inactive rejection,
  hash-check state race, stale revision and protected append-only old references.
- `tests/test_edition_persistence.py`: migrated file-SQLite concurrent writers and
  independent interpreter reopen, same UUID/preferences/assignments and DB integrity.
- `browser/test_editions.py`: German preference/reset and explicit pinned-choice
  check across preference change/reload, local assets, unchanged synthetic PDF bytes.
- Full Linux/container/security CI `45027269366` on `9c0ecd2` passed: 572 tests,
  ten browsers; actual image preference creation and restored preference/history
  verification added to the existing non-root, RAW-read-only, network-disabled flow.

## WP-23b (merged, software verified)

- AR-18/EX-03/EX-07: `tests/test_downloads.py` exercises unchanged direct PDFs,
  bounded ZIP member/order/hash, combined A3/A4 document once, no member/project
  dependency, auth/CSRF, duplicate/path/size/actor/stale token rejection, withdrawn/
  pending/corrupt states, staging races, immutable response bytes, scratch no-follow
  and lock/temporary cleanup. Confirmed derivative preview requires own approval.
- `browser/test_downloads.py` verifies actual PDF/ZIP downloads, signed selection
  confirmation, original hashes, combined parts and no external browser requests.
- Actual hardened image PDF/ZIP staging added to `scripts/publication_smoke.py`;
  full CI `45030782487` on `bcc2e5b` passed: 590 Linux tests, eleven browsers and
  complete image/Compose/unchanged downloads/restore/installation/security checks.
  Private NAS/hardware acceptance remains separate; no real installation data used.

## WP-29 (merged, software verified)

- PR-01/05/07: `tests/test_projects.py` validates durable settings/revisions,
  same-title identities, full graph duplication/remapped FKs/guests/reserves,
  source isolation, protected history and archived edit denial; incompatible
  editions/variants, cross-project/scoped identity changes, revalidation bypass,
  cyclic replacements and SQLite uniqueness rejected. UI auth/CSRF/escape/409.
- `tests/test_project_persistence.py`: independently migrated file-SQLite
  competing edits (one success/one conflict), separate interpreter reopen,
  stable reserve/clone/revision identities and actual database integrity.
- `browser/test_projects.py`: real German CRUD/duplicate/archive and stale
  concurrent editor. Updated shell navigation assertions retain unavailable
  scan/settings checks. Actual hardened image project CRUD/clone smoke added.
- Full CI `45034660243` on `8aad238` passed: 601 Linux tests, twelve browsers,
  image/Compose/actual project graph on isolated restored SQLite/security checks.
  No private NAS data or hardware acceptance is implied by software verification.

## WP-30 (merged, software verified)

- GR-07/12, PR-02/03/06: `tests/test_piece_list.py` covers reserve consuming number,
  3→1 renumbering, repeated arrangement independent UUID, fill/replace same slot,
  acknowledgement/revalidation/history, removal retention, complete ID-set checks,
  stale/archived denial, mid-order atomic rollback, no personal list, limits/auth/CSRF.
- `tests/test_piece_list_persistence.py`: competing file-SQLite complete reorder
  requests, one success/one conflict; separate restart checks dense numbering/reserve.
- `browser/test_piece_list.py`: actual drag/drop local contents preview/save/reload,
  live substring library search and reserve fill, repeated arrangement addition.
  Existing hardened image project smoke now exercises insert/move/reserve clone.
- Full CI `45039372553` on `5e6299d` passed: 616 Linux tests, thirteen browsers,
  actual container shared list/backup/restore and vulnerability/secret checks.
  Browser input waits for actual live-search enhancement readiness. No NAS claim.

## WP-31 (merged, software verified)

- CAT-02/PR-04/AS-01: `tests/test_participants.py` validates bounded subset/all/none,
  name/instrument filters, actor/project/revision-bound page selection, guests without
  permanent members, saved defaults unaffected by master edits, explicit revision/name
  refresh and manual defaults, personal overrides/roles/shared list untouched, retained
  deselection/clone identity, invalid/stale/inactive/archived rejection and batch rollback.
- `tests/test_participant_persistence.py`: independently migrated SQLite concurrent
  refresh (one success/one conflict), separate interpreter reopen of saved default,
  member revision and unchanged per-position override, actual DB integrity.
- `browser/test_participants.py`: actual subset/guest selection then private synthetic
  master change between browser phases; no default change before explicit refresh.
  Hardened image smoke includes saved member default and project-local guest.
- Full CI `45043669400` on `da915e6` passed: 630 Linux tests, fourteen browsers,
  actual image saved participant/guest/shared list/restore and security checks.
  No real members/music/NAS data were used; private acceptance is not implied.
- Final PR #32 CI `45045456240` and bounded navigation correction PR #33 CI
  `45047209870` passed. Main CI `45048123486` on merge `53aaced` verified all 630
  Linux tests, fourteen browsers and complete actual container/security gates.

## WP-34 (merged, software verified)

- CAT-04/AS-07: `tests/test_ensemble.py` covers four roles/seven participants,
  same role on distinct exact variants/notation, position-over-project mapping,
  explicit clear, missing/inactive/foreign/duplicate/retarget rejection, role
  protection, unchanged defaults, stale/archive denial and pinned history/clone.
- `tests/test_ensemble_persistence.py`: independent migrated file-SQLite competing
  mapping writes (one saved/one conflict) and separate interpreter integrity/reopen.
- `browser/test_ensemble.py`: German role/mapping/participant editing, incompatible
  variant rejection and explicit reset with persisted independent defaults.
- `scripts/publication_smoke.py`: actual non-root/no-network/read-only RAW container
   role/participant/mapping acceptance added. Full CI `45057377256` on `424defd`
   passed: 646 Linux tests, fifteen browsers and all actual container/security gates.
   Local full regression 565 passed/81 platform skips. No private NAS claim.
- Queue regression prerequisite: immediate enqueue uses the SQLite statement clock
  already used by claims; `test_immediate_enqueue_uses_database_clock_not_future_python_microseconds`
  proves future Python-default skew cannot delay immediate claims. Existing lease/
   cancellation/print-retry assertions retained; local 43 queue/lifecycle tests passed.

## WP-35 (merged, software verified)

- CAT-03/AS-05/06: `tests/test_rules.py` covers global/project/position precedence,
  effective overlay cycles and clear exposing inherited cycle, same-variant explicit
  one-hop replacement, foreign/reserve/stale/duplicate denial, confirmed exact edition
  scope, hash-check race, reset/history/clone and no silent withdrawn pin replacement.
- `tests/test_rule_persistence.py`: migrated global revision singleton and competing
  file-SQLite rule writers, one saved/one conflict; independent reopen/DB integrity.
- `browser/test_rules.py`: authenticated global/position rules and concrete confirmed
  project edition selection and explicit reset; no external browser requests.
- Actual image global/project replacement smoke added. Full CI `45062571782` on
  `22edbd9` passed: 661 Linux tests, sixteen browsers and actual container/security
  gates. Local regression 578 passed/81 platform skips plus final targeted reruns;
  private NAS/hardware acceptance is separate and was not performed.

## WP-32 (merged, software verified)

- GR-09/10, AS-01/05/06/07: `tests/test_resolution.py` exercises saved-default/
  personal/role precedence, position/project/archive/sole/explicit editions, manual
  part 2 when 3 exists, variant-specific role, no fallback on ambiguity/invalid pin/
  corruption/revalidation, explicit one-hop replacement/cycle checks, missing copies,
  source-missing retained versions, immutable provenance, no-query pure selection
  and one verified read per file/session. No view duplicates musical resolution.
- `tests/test_resolution_persistence.py`: independent migrated process/reopen with
  actual synthetic confirmed copy and exact resolver IDs/hash/default provenance.
- Actual hardened container resolver added; existing browser suite retained. No
   matrix, preflight, generation, missing acknowledgement or NAS acceptance claimed.
- Complete CI `45068374035` on `f20655e` passed: 685 Linux tests, sixteen browsers,
  actual container resolver/confirmed-input restore and security checks. Container
  fixture uses exact preferred assignment, not arbitrary catalog row order.

## WP-33a (software verified; integration pending)

- AS-02/AS-08: `tests/test_matrix.py` compares displayed cells with WP-32 results,
  Mathias/Sebi/Riccardo manual override and provenance, selected-only columns,
  shared slot numbering/reserves, auth/POST denial/no mutation/escape, bounded
  pagination, invalid/missing-role/corrupt/substituted labels and per-file read reuse.
- `browser/test_matrix.py`: actual German shared matrix and personal edition,
  reserve without controls, reload, local-only requests and mobile width containment.
- Hardened actual image matrix presentation adapter acceptance added; no direct
  edits, preflight/generation or private NAS acceptance claimed.
- Full CI `45073173161` on `800dd5a` passed: 696 Linux tests, seventeen browsers,
  actual hardened image matrix/restore and security checks. Corrected local full
  regression 615 passed/81 platform skips. No private NAS acceptance inferred.

## WP-33b (software acceptance)

- AS-03/AS-08: `tests/test_matrix_edits.py` exercises exact signed actor-bound
  confirmed part/notation/version, stale/foreign/reserve/expired/corrupt/withdrawn
  and post-hash race rejection, one person's override only, old/new protected audit,
  default keeping existing overrides, no-JS/HTMX POST/auth/CSRF/conflicts and bounds.
- `tests/test_matrix_edit_persistence.py`: actual migrated SQLite concurrent cell
  writes (one success/one conflict), independent reopen/central exact provenance.
- `browser/test_matrix_edits.py`: local HTMX edits/partial refresh, stale second tab,
  saved default keeping manual edition and reload, unchanged reserve/common list.
- `tests/test_htmx_asset.py`: official local asset hash/license/safe config; no CDN.
  Existing reserve test scoped to reserve rows after approved cell editors elsewhere.
- CI `45084352726` on `2b6eec1`: 714 Linux tests, eighteen browsers and full
  hardened image/synthetic exact edit/security checks passed. Local full regression
  631 passed/81 skips before final coverage, covered by targeted 18-test rerun.
  Final PR CI `45085495233` and merged main CI `45086565420` passed; PR #39
  merged as `88ef45a`. No NAS acceptance inferred.

## WP-33c (software acceptance)

- AS-04/AS-08: `tests/test_matrix_batch.py` covers atomic exact same-person
  part/notation multi-edit, complete validation/fencing and audit rollback,
  invalid/foreign/reserve/duplicate/withdrawn/corrupt/stale selections, scope and
  bounds, single/multi reset, historical pins/protection, defaults preserving
  overrides, clone state, missing/revalidation statuses and authenticated CSRF forms.
- `tests/test_matrix_batch_persistence.py`: actual migrated SQLite competing batches
  (one save/one conflict), one-cell reset and independent process reopen.
- `browser/test_matrix_batch.py`: real associated cell forms in HTMX, invalid batch
  no changes, multi-save, stale second tab, single reset/reload, unchanged reserves/list.
  Actual JavaScript-disabled selected-reset submission also checked; 21 focused
  batch/persistence tests and all nineteen browsers passed on final implementation.
  Local full regression 652 passed/81 platform skips before final refinements;
  final 49 matrix/edit/batch/persistence tests and all three matrix browsers passed.
  CI `45090329532` on `04d2ff0` passed: 736 Linux tests, nineteen browsers,
  hardened image/Compose actual synthetic batch/reset and full vulnerability/secret
  checks. Final documentation-head/merged-main gates remain. No NAS acceptance
  or preflight/generation completion inferred.
# Current-feature Synology test distribution

OP-01–06, GR-01–15, UI-01–03: `tests/test_feature_availability.py`,
`tests/test_synology_distribution.py`, `scripts/synology_stack_smoke.py` and
`browser/synology_stack.cjs` extend the existing acceptance. The real NAS-profile
Compose/TLS browser scenario exercises index/manual review/publication, matrix,
missing acknowledgements, reading/print/excerpt/contents and downloads; actual
worker publication crashes/cancellation/failure/pins/RAW/persistence use Linux
containers and isolated synthetic binds. New scenarios are not verified until
the corresponding final-head CI succeeds. Physical DSM acceptance remains separate.
