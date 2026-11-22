# Implemented acceptance traceability

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
