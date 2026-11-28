# Progress record

## Compound recognition follow-up batch — 2026-11-28 (in progress)

- PR #96 is frozen at `b99732d145857b5978b919e5508bad23f8b21df9` during
  its exact-head Foundation/Container/Windows wait; no result is claimed yet.
  Safe follow-up work continues on `feat/compound-recognition-batch` based on that
  candidate; its integration remains dependent on the preceding verified merge.
- Added conservative, bounded exact catalog-heading observations from native OCR
  line identities. Side-by-side and repeated headings retain separate image-pixel
  locations; equal titles remain ambiguous. No musical boundaries, continuation
  relationships, splitting or approval are inferred. Whole-page/booklet use remains
  independent. Review displays at most 16 observations only when the current rule
  context still matches immutable evidence. Legacy evidence remains readable.
- Focused compound/selection tests: 42 passed. No full CI, native OCR accuracy,
  browser execution or manual acceptance is claimed for this follow-up checkpoint.

## OCR region/review integration batch — 2026-11-28 (in progress)

- PR #95 merged at `3766fe389be7cc66489e8446858a8e7a462b449a` after final-head
  `cb896134a2bbbed123131ce3935c5b9030f26112` passed Foundation, Container and
  Windows. Exact post-merge run 46118104077 passed Foundation, Container and
  Windows on the same Main SHA. The initial 30-minute wait timed out while the
  browser step ran; one bounded extended wait confirmed success without cancelling
  the run. Main is the verified comparison baseline for this independent batch.
- DEC-17 permanently separates checkpoint commits from integration boundaries.
  Reconciled AGENTS, PROCESS, standard checks and the implementation plan. Actual
  workflow triggers already support CI-free pushes to feature branches without an
  open PR; Main is unprotected and the manual reviewed-green gate still applies.
  No workflow/protection weakening is needed. Requirements/CI contract checks:
  8 passed; structural requirements checker: no errors.
- Continue on `feat/ocr-region-review-batch`: selected-page/region OCR, visual
  evidence and review improvements form one cohesive batch with targeted checks
  and focused checkpoint commits. Full combined verification/review and exact
  PR/Main CI will occur at the integration boundary, not each checkpoint.
- Backend increments now support selected physical pages/displayed rectangles,
  exact rotated CropBox/UserUnit conversion, independently idempotent queue
  payloads and authenticated hash-verified source-image evidence. Focused backend
   geometry/queue/preview tests pass; graphical drag selection, keyboard fields,
   source-page navigation and bounded escaped image/word evidence are implemented.
  Added independent PDF-text/OCR conflict comparisons and conservative fallback
  to readable text-layer evidence: 24 focused recognition/service tests passed,
  one platform-specific recovery test skipped locally. No musical approval changes.
  Native selected-region OCR smoke is prepared for the final container gate, not
  claimed locally executed. Segmentation/continuation acceptance remains open.
- Focused recognition fixes bind cache rule versions to alias targets, duplicate
  work identities and part/instrument relationships (26 passed, one local skip).
   Native OCR line identities retain separate side-by-side headings instead of
   merging them by vertical position. Profile version now advances to `page-v3`.
- Reproduced clipped-out text leaking through ordinary PDF extraction, then added
  bounded geometric text extraction inside the existing isolated PDF worker for OCR
  selections. Four rotation regressions and related PDF/OCR checks: 64 passed,
   one local platform skip. No original bytes, musical regions or approvals changed.
  Additional selected-evidence checks cover a different source version containing
   identical bytes, incomplete historical evidence and GET-only private rendering:
   23 backend tests passed (the pending UI launch test was not included).
   Conservative clipped-out native character limits, logical page ordering and
   cumulative text limits: 6 real-PDF regressions passed.
   Selection/review, real-PDF and traceability checks: 55 passed. Browser checks
   cover drag/keyboard/reset/zoom; they are prepared but not locally executed
   because Node/browser tooling is unavailable. Independent cumulative review
   was completed below; no new full CI or manual acceptance is claimed.
  Checkpoints through `55780cf` are pushed on the feature branch without an open
  PR (CI-free remote recovery checkpoint under the verified current triggers).
   Uncommitted selected-page/evidence changes are not included in that checkpoint.
- Independent cumulative review identified incorrect displayed dimensions in native
  text clipping for non-square 90/270-degree selections. Corrected extraction to
  unrotated page bounds; eight additional native regressions cover omissions and
  outside-text exclusion. Profile `page-v3` invalidates affected older evidence
  contexts. Focused PDF/OCR/selection checks: 51 passed. Browser fixture now covers
  two-page selection synchronization and actual selected-job submission without
  inspection. Independent follow-up reproduced the original failure cases across
  all four orientations and confirmed the fix with no remaining implementation
  blocker. Strengthened the stored regression positions to reproduce both original
  defects (14 real-PDF tests passed). Final browser/CI execution remains pending.
- Final focused combined OCR/recognition/review/preview/PDF/traceability/workflow
  checks: 121 passed, two platform-specific local skips; Ruff and formatting pass.
  Independent cumulative review and focused follow-ups have no unresolved finding.
  Browser fixture additionally decodes the protected source image and navigates
   from its evidence before submission. Combined local regression completed with
   1413 passed, 161 skipped and two failures in existing source-reader fixtures:
   this Windows account cannot create symlinks (`WinError 1314`). This is an
   environment-limited failing run, not a green suite. It began before the final
   rotation fixes; the focused checks above cover those changes. Requirements,
   Django checks and migration consistency pass. The combined candidate proceeds
   to mandatory exact-head Foundation/Container/Windows CI; integration and
   representative manual/physical acceptance remain unverified.

## Approved OCR product phase — 2026-11-27 (in progress)

- Verified clean Main baseline `b536d8d286e13b1f10a2a872baf999aec01d0b76`
  and successful exact Main run 46060645008 (Foundation, Container, Windows).
  WP-54/55 are complete within their verified software scope; their earlier
  investigations and successful acceptance are not reopened.
- On `feat/ocr-product-phase`, integrated the owner's DEC-16 requirements and
  priority amendment: optional intact booklets/segmentation, OCR evidence, core
  optional classification/duration, faceted search and per-user filter visibility.
  Advanced custom metadata/saved searches/external integrations remain secondary.
- German permanent manual plan `docs/MANUAL_ACCEPTANCE_TESTS.md` now contains
  61 stable scenarios with availability, concrete actions, expected results and
  execution/defect fields. Coordinator review corrected stale OCR availability,
  invalid references and independent whole-work/movement approval semantics.
  Independent documentation review confirmed scenario coverage; its three findings
  (cache retention, explicit correction rather than automatic review tasks, and
  independent hardware prerequisites/synthetic fixtures) were corrected.
  All physical/manual results remain unexecuted.
- Audited both workflows and upgraded supported full-SHA Node 24 actions,
  preserving ZIP recovery, permissions and all checks. Local Node/npm are absent;
  browser verification stays required in CI. PR #95's first exact-head CI is green;
  final manual-plan documentation and final-head integration checks remain pending.
- Implemented the first partial WP-24/25 OCR increment: all-page local Tesseract,
  exact verified CLEAN input, bounded owned subprocesses, per-page immutable
  runtime/profile/geometry/rule cache, persistent progress/cancellation and explicit
  launch from review. OCR proposals never change approval or assignments.
  Targeted local OCR/services/PDF/review/process tests pass. Independent Sol review
  and focused fix review found no unresolved blockers after correcting container
  imports, fenced scratch recovery and native package cache identity.
  Exact commit `a2e178fd90f0a276e54e5ed932f048303c7c1910` passed run
  [46073430077](https://github.com/tostman1/notenarchiv/actions/runs/46073430077):
  Foundation (including browser), Container (including native text/image-only OCR
  smoke and POSIX recovery) and Windows. Review evidence is recorded on PR #95.
  This establishes synthetic software verification, not recognition accuracy or
  manual/physical acceptance. Full WP-24/26/56 is not done.
- Local full-suite execution exceeded the 1,200-second tool deadline and was
  terminated (exit 143); this is unverified, not a regression or a pass. A later
  full run completed: 1,368 passed, 158 skipped and the same two local
  WinError 1314 symlink fixture failures (1,162.45 seconds). Focused checks cover
  the subsequent recovery/cache and confirmed-reanalysis changes.
  The Windows shared-runtime diagnostic completed:
  374 passed, 6 skipped, 2 failed at synthetic symlink creation with WinError 1314
  (local account lacks the required privilege), before application assertions.
  No security settings or tests were weakened; exact Windows CI remains required.
  Successful targeted evidence is retained; required full CI gates are unchanged.
- Next: integrate this reviewed increment, then region evidence, compound
  recognition and visual correction. No real
  archive access, NAS deployment or native Windows writes are authorized here.

## Consolidated WP-54/55 acceptance — 2026-11-27

- The existing #75–90 backlog is integrated with exact post-merge Main verification.
  #91 completed bounded 125-edition worker publication; Main run 46034210052 passed.
  #92 completed explicit signed shared-page policy; Main run 46050512807 passed.
- #93's independently reviewed read-only integrity report merged at
  `8af05815fbb18f830d7b9acad1ca5a2578a6d140`; exact Main run 46053275101 passed
  Foundation, Container and Windows. WP-54 and WP-55 implementation and applicable
  synthetic acceptance are verified at this checkpoint.
- `docs/wp54-55-acceptance.md` consolidates implementation, synthetic migration,
  historical replay, browser and POSIX worker evidence. Earlier open statements below
  are historical checkpoints, not the current implementation inventory.
- The remaining delivery gate is this documentation's reviewed integration and exact
  post-merge CI. No further product implementation is required for WP-54/55.
  Physical NAS acceptance, real-data migration and native Windows writes remain separate.
  No OCR, compound scan segmentation or subsequent major package is started.

## Read-only additive integrity evidence — 2026-11-27

- OP-08 now has `check_content_integrity`: bounded, read-only SQLite and relational
  history checks with compact JSON counts and failure codes. It checks source-page
  mapping inventories and content manifests/references without exposing paths,
  titles, actors or hashes. It never repairs data or derives musical confirmation.
- Stale confirmed revisions remain valid historical evidence. Byte verification,
  current-use eligibility and physical NAS acceptance are separate checks.
- Two synthetic tests passed, including interrupted mapping detection without repair
  and retained historical confirmation after a logical revision. Ruff passed.
- #91 has merged; its exact post-merge Main gate is running. #92 has green exact-head
  CI and reviewed policy changes, awaiting that gate. WP-54/55 completion documentation
  remains open; native Windows writes stay disabled and no deployment is authorized.

## Explicit shared-page selection — 2026-11-27

- The entire #75–90 stack and exact Main `afafd3983fe72fa365832a228a69351576d3bb1d`
  passed Foundation, Container and Windows (Main run 46024076263).
- #91's exact head `fc9d1061939f8296ac1b313f78d07447d43034b2` passed all required
  checks, including the synthetic POSIX 125-edition worker acceptance. Review and
  integration remain pending; no physical booklet or NAS acceptance is claimed.
- Confirmed-content export now exposes explicit region extraction, complete-page
  preservation once, or complete-page repetition. Signed authorization and immutable
  payloads retain the chosen policy and deterministic per-occurrence consequences.
  The preview reports emitted pages; all original musical occurrences remain pinned.
  Whole-page modes additionally require independently confirmed whole-file approval:
  a partial region inspection never approves unknown surrounding music.
- Eighteen targeted policy/export/view/pin/traceability tests passed; Ruff, Django,
  migration drift and whitespace checks passed. Intermittent fixture integrity failures
  did not recur on the unchanged final targeted run;
  this is not a full CI gate. New exact-head CI and final package acceptance remain open.
  A bounded exception-tracing diagnostic completed with 13 passing tests and no
  verification exception, so the intermittent local fixture cause is not established.
  Follow-up checks passed 11 policy/view/traceability tests. Historical whole-page
  snapshots require a recorded consequence plan, and manifests carry policy/plan.
  WP-54/55 are still in progress. Native Windows writes remain disabled; no subsequent
  OCR/segmentation package, real-data migration or production deployment was started.

## Full-booklet export completion — 2026-11-27

- Existing stacked PRs #75–90 are integrated without rewriting their verified
  heads. Exact post-merge Main CI passed through #89; #90's Main CI is pending.
- WP-54/55 remain **in progress** pending final acceptance and traceability.
  Production shared matrix, signed schema-3 authorization, protected historical
  project inputs and the actual worker/browser path already exist. Older entries
  below describe their checkpoint state, not current missing features.
- Confirmed-content selection and its historical reader now share a bounded
  125-edition limit. Existing 16-file, byte, parser, output and snapshot limits
  remain unchanged.
- Added synthetic POSIX acceptance for 125 independently inspected editions
  through signed authorization and the durable worker, explicit repeated shared-page
  occurrences, historical replay after a logical revision and one unchanged BASE.
  Its actual POSIX result is pending CI; this Windows host skips that test.
- Local targeted checks: four passed, two POSIX tests skipped; Ruff, Django checks,
  migration drift and whitespace passed. No real-data migration, deployment or
  physical/NAS acceptance. Native Windows writes remain disabled under DEC-15.

## Interrupted additive document mapping acceptance — 2026-11-26

A deterministic interruption after the first committed 100-source mapping batch
retains its receipts. Restarting the existing bounded backfill completes the
remaining five sources; another run preserves all deterministic UUIDs and source
counts. The transactional test passed in 6.63 seconds. This is synthetic database
recovery evidence, not NAS power-loss or real-data migration acceptance. Exact CI
and integration gates remain required; WP-54/55 remain in progress.

## Unreadable content preflight acceptance — 2026-11-26

A deterministic isolated-parser rejection now exercises the content branch of
shared preflight: retained visual confirmation does not override an unreadable
PDF, the cell is blocking, signed authorization creates no snapshot, and earlier
confirmation history remains intact. The targeted test passed in 6.61 seconds.
Exact CI and preceding integration gates remain required. WP-54/55 remain in
progress; native Windows writes remain disabled.

## Mixed historical project input acceptance — 2026-11-26

One shared schema-3 authorization now exercises an inspected two-occurrence
content edition alongside an explicit personal whole-file edition. The exact
disjoint relational pin inventories survive a subsequent logical-page edit;
historical generation retains both ordered music positions and 2/1 page counts.
The targeted test passed in 10.61 seconds. Ruff and traceability checks are local
evidence only; exact CI and preceding integration gates remain required.
WP-54/55 are not yet marked complete, and native Windows writes stay disabled.

## Synthetic mass and movement sequences — 2026-11-26

A parent composition and three independent equal-title movements have separate
inspected editions spanning two published sources. Explicit shared-page and
continuation occurrences render as 1/2/1 pages for the movements and four pages
for the complete composition, without merging identities or approving either
whole source. Historical capture reproduces the complete ordered sequence.
The targeted acceptance test passed in 12.50 seconds; this is synthetic evidence,
not physical/NAS acceptance. Integration and remaining WP-54/55 gates stay open;
native Windows writes remain disabled.

## Complete synthetic instrumental booklet — 2026-11-26

All 125 independent equal-title works now have explicitly inspected editions for
two instrumental sources: 250 confirmed sequences across 32 pages per source,
four rectangular cards per page, reversed instrumental locations and selected
continuations. Unconfirmed sequences are rejected before review; exact logical
pins, occurrence identities and historical capture remain reproducible without
whole-file approval. The targeted acceptance test passed in 38.66 seconds.
This synthetic evidence is not physical booklet/NAS acceptance. WP-54/55 delivery
and integration gates remain open; native Windows writes stay disabled.

## Shared project content browser acceptance — 2026-11-26

A synthetic same-origin browser scenario verifies that the matrix displays the
inspected edition, excerpt preflight exposes its original context, tampered
authorization is rejected, and replay creates only one schema-3 content-pinned
run. The browser scenario requires the existing CI Node/Chrome environment and
has not run locally. It does not approve music or execute production deployment.
Full integration and WP-54/55 acceptance remain open; Windows writes stay disabled.

## Production report fixture schema correction — 2026-11-26

Exact PR #84 and #85 CI failed the same existing endpoint test: its fixture
signed a legacy schema-1 report while production preflight now requests schema 3.
The signature mismatch correctly returned HTTP 409. The fixture now explicitly
requests the production schema for that endpoint test; legacy service tests keep
their schema-1 coverage. No signature, CSRF, eligibility or application safeguard
is weakened. Sixteen snapshot/preflight tests passed in 45.22 seconds and Ruff
passed. Fresh exact-head CI is required before integration; the failed heads
are not merge-ready.

## Shared project content presentation — 2026-11-26

The production matrix and full/excerpt preflight now request the same inspected
content resolver and schema-3 authorization path. Content cells show their exact
edition/context instead of constructing invalid whole-file download links.
Session-local publication verification is cached by file identity, revision and
hash, while current content eligibility is rechecked for each cell. Thirty-one
targeted presentation, resolver and traceability tests passed. Legacy outcomes
retain their original dataclass contract. A synthetic POSIX worker acceptance
test covers signed FULL content generation after a logical revision changes;
it has not run locally on Windows and exact CI remains required. WP-54/55 are not marked complete. Native
Windows writes remain disabled and no production deployment is authorized.

## Opt-in project content preflight and authorization — 2026-11-26

The shared preflight can explicitly capture schema-3 inspected content through
the existing resolver. Signed authorization rechecks content revision, geometry,
confirmation, publication and source dependencies under the SQLite writer lock
and creates protected per-cell historical pins. Existing default schema-1 callers
remain unchanged. Twenty-nine targeted preflight and snapshot tests passed;
Django checks, Ruff and whitespace checks passed. A changed logical revision
rejects reuse of an old authorization while the saved snapshot remains readable.
Matrix/UI activation, end-to-end worker acceptance and complete WP-54/55 gates
remain open. Native Windows writes stay disabled; no production data was used.

## Versioned project worker input path — 2026-11-26

The existing generation loader and composer now recognize schema-3 project
content pins alongside protected legacy whole-file pins. Complete participant,
position and usable-cell inventories are checked before historical rendering;
content in an old schema is rejected. Mixed composition retains exact order,
missing acknowledgements and reserves, with bounded input/output bytes. Eleven
targeted project-pin, snapshot-persistence and generation/export checks passed.
No project authorization currently produces this schema: shared dependency and
preflight capture remain open, so WP-54/55 are still in progress. Existing
schema-1 behavior and native Windows write disabling remain unchanged.

## Versioned shared project content resolution — 2026-11-26

ResolutionSession now supports explicit opt-in content candidates while retaining
the identical part, replacement and edition-priority engine. Default legacy
callers and their payload shape remain unchanged. Content results pin exact
ordered inspected inputs, verify publication bytes and reject changed revisions;
an unavailable archive preference never falls back. An explicit personal legacy
choice still wins. Twenty-eight targeted resolver/adapter/preference tests passed,
followed by three focused tests after adding explicit-choice parity coverage.
Authorization, dependency capture, matrix/preflight and worker integration remain
open; WP-54/55 are not complete. Native Windows writes stay disabled.

## Project content snapshot validation — 2026-11-26

The historical project reader now validates the snapshot record and rebinds both
payload and preflight fingerprints before consuming relational pins. A direct
SQL pin-update test exercises the immutable-history guard, and a tampered
preflight digest is rejected. Thirteen targeted project-pin, content-export and
traceability checks passed; Ruff and whitespace checks passed. This closes the
bounded independent-review follow-up without enabling project authorization or
changing historical payloads. WP-54/55 remain in progress; Windows writes remain
disabled.

## Historical project content assembly — 2026-11-26

The schema-3 personal assembly service now renders exact historical content-cell
pins through the shared bounded vector-region renderer. Pinned project order and
titles survive subsequent logical revisions; explicit missing acknowledgements
and reserve positions produce placeholders without silent omission. Thirteen
targeted project-pin, archive-content and traceability tests passed; Ruff and
Django checks passed. This service is not yet activated by project authorization
or the generation worker; the cohesive shared resolver/preflight integration
remains open, and WP-54/55 are not complete. Main #70 exact CI 45889494523 passed;
#71 was integrated with its exact post-merge CI pending. Windows writes stay disabled.

## Protected project content-cell pins — 2026-11-26

An additive schema-3 relational cell pin now records exact project position,
participant, playable part and inspected content confirmation. Its bounded
historical reader validates the immutable payload without selecting current
preferences or newer logical revisions. SQLite guards protect referenced file
identity and pin updates. The new historical-revision, tampering and file-guard
test passed; 18 existing content-input/snapshot regression tests also passed.
Django checks and migration drift passed. Authorization, the shared project
resolver and generation do not yet activate this schema; WP-54/55 remain in
progress. Native Windows writes stay disabled.

## Project ordered-input compatibility boundary — 2026-11-26

The shared project ResolutionSession now exposes its exact selected legacy edition
through the uniform ordered-input contract. It preserves missing/ambiguous/reserve
outcomes, selected identities, bytes/path/revision pins and read-only project state;
it rejects concurrent resolver changes instead of substituting. Twenty-five
project adapter/resolver checks passed. This additive bridge does not yet activate
content editions in project snapshots or generation; that versioned integration
remains open, so WP-54/55 are still in progress. Main through #69 passed exact
CI run 45885633566; #70 merged with its post-merge CI pending. Native Windows
writes remain disabled.

## Instrument-specific card-region acceptance — 2026-11-26

A synthetic acceptance case now renders four explicitly reviewed card regions
from each of two instrument sources, with different coordinate ordering for the
same arrangement. Unknown proposals are unusable. Changing one region invalidates
only that instrumental edition for new use, while historical captured inputs and
the other edition remain usable. No whole-file musical confirmation is inferred.
The case passed locally with the isolated PDF processor; this is not physical
booklet or NAS acceptance, nor completion of shared project content activation.
Exact #73 and #74 CI passed, including their browser and POSIX worker acceptance;
their dependency integration remains pending. Native Windows writes stay disabled.

## Compound publication command — 2026-11-26

`publish_compound_source VERSION_UUID --title TITLE` exposes the neutral durable
COPY service through a bounded administrative command. It returns the queued job
UUID, grants no musical approval, and sanitizes storage/validation errors. Four
command/naming checks passed locally. Product WP-54/55 remain in progress; native
Windows publication is still disabled. Main through #68 passed exact CI on
`416e9f2fcacabb7b886c40b39ec8df1ab2669742` (run 45882493576). #69 has now
merged; its exact post-merge Main CI is pending, not verified by the earlier PR CI.

## Neutral compound source publication — 2026-11-26

Independent retained-catalog review found no blockers. Its two coverage gaps
are now exercised: numeric stale withdrawal and inactive-work replacement both
leave the original current association and receipt intact. Four correction/UI
checks passed. The catalog detail deliberately labels withdrawn history separately
rather than advertising historical associations as current.

Compound copies receive a readable `Sammlungen` path under the stable source
document identity. Existing BASE publications and acknowledged paths are reused;
title changes never rename history or duplicate source bytes. The existing COPY
worker, verified staging, collision reservation and recovery remain unchanged.
No musical assignment or whole-file confirmation is granted by this operation.
One naming/delegation contract check passed; two real POSIX worker checks are
skipped on this Windows host and remain required exact-CI acceptance. WP-54/55
remain in progress, including shared project content activation. Native Windows
writes remain disabled; no deployment or actual archive migration occurred.

## Explicit catalog correction editor — 2026-11-26

The first exact browser CI failed at the action selector: Django renders the
accessible form label as `Aktion:` while the new script requested exact `Aktion`.
The selector now tolerates the normal label suffix, with a client regression
asserting the replacement editor exposes the action control. The failed gate
is not treated as success; the corrected head requires fresh exact CI.

Authenticated, CSRF-protected correction screens expose reason-bound withdrawal
and membership replacement with submitted revision fences. Work details link to
current and retained association history. GET does not mutate; duplicate/stale
replacement fails without losing the original row. Seven correction/collection
checks and 23 catalog/view regression checks passed; Ruff and Django checks
passed. Browser acceptance and exact CI remain pending. This increment does not
claim complete WP-54/55 or change approval, historical exports, deployment or
the disabled native Windows writable path.

Real-browser correction coverage now exercises explicit replacement, stale
duplicate rejection and withdrawal of the replacement, with original receipt
and both history events retained and no generation snapshot. Nine targeted
correction/view/traceability checks passed; Node is unavailable locally, so
browser execution remains an exact-CI gate, not a claimed local result.

## Retained catalog corrections — 2026-11-26

Explicit actor/reason-bound withdrawal events now retain memberships,
relationships and alternative titles. Atomic membership correction preserves
the old provenance receipt and rolls back withdrawal if replacement validation
fails. Current reads exclude terminal events; containment validation ignores
withdrawn edges. SQLite guards retain history and enforce occupied positions
among current associations, including bulk inserts. Ten targeted correction,
collection, migration/isolated-restore and disposable-test isolation checks
passed in 11.23 seconds; Ruff, Django checks and migration drift passed.
This service-level increment has no catalog editor yet. Do not downgrade after
replacement rows reuse historical positions: use a schema-compatible backup.
WP-54/55 remain in progress, including shared project content activation and
neutral compound publication. Native Windows writes remain disabled.

## Incremental compound identity acceptance — 2026-11-26

A synthetic 125-work collection now exercises repeated titles with independent
UUIDs, six explicitly inspected editions across two playable instrumental parts,
shared page references, differing continuation counts and orientation, unknown
remaining content and exact capture/load parity. No whole-file approval or
assignment is inferred. Four compound/collection tests passed in 9.49 seconds;
Ruff and formatting passed. This is bounded identity/confirmation acceptance,
not a complete 125-piece region-segmentation or physical booklet acceptance.
WP-54/55 remain in progress, including project activation, neutral compound
publication and correction/withdrawal workflows. Native Windows writes remain
disabled; no actual notes, production migration or deployment were used.

## Explicit content preference editor — 2026-11-26

An authenticated, CSRF-protected editor now exposes setting and clearing the
exact arrangement/part preference with the submitted arrangement revision.
The service retains explicit confirmation eligibility, CAS and actor/history
validation. GET does not mutate; stale and changed-content submissions fail
closed. The German UI explicitly states that this action does not confirm music
and that full project content activation remains incomplete. Six targeted
preference/editor/export-view tests passed. A real-browser scenario now covers
setting, stale clearing, explicit current-revision clearing and retained history
without creating an export. Nine targeted preference/editor/traceability tests
passed; Ruff and formatting passed. Browser execution remains CI-only because
Node is unavailable locally; exact CI for this updated delivery remains pending.
WP-54/55 remain in progress. Native Windows writes
remain disabled; no real-data migration or deployment was performed.

PR #66 is exact-head green at `64eee0bd`; #68 at `c9096f5b` is also green.
PR #67's `1af2aa2b` Container check failed during synthetic index submission
with HTTP 500, before any job was queued; Foundation and Windows passed.
The log did not expose the application exception. One failed-job rerun passed
all required checks on unchanged exact head `1af2aa2b`; the root cause remains
unproven. PR #65 was integrated and its exact Main CI passed at `27dc7e16`
(run `45873274859`). PR #66 was subsequently integrated at Main `d67186d1`;
its exact Main CI (run `45876729842`) remains pending. PR #69 is exact-head
green at `1a1dbcdffb4538c3afbba39abaaf3056a917601a` after independent review
and history/rollback coverage corrections. Remaining integrations retain their
review and exact post-merge CI gates.

## Unified archive preference persistence — 2026-11-26

Independent Qwen review found no blockers. Follow-up now enforces history input
kind exclusivity in SQLite constraints as well as model validation. Additional
assertions cover numeric stale revisions, explicit clearing, and rollback when
actor validation fails after CAS. Fifteen preference/legacy tests passed after
these corrections. The project reason-code distinction is deferred to its
complete content-contract UI activation; no substitution is enabled.

The additive preference scope can now select either a confirmed legacy assignment
or explicitly confirmed content edition, never both. Short SQLite CAS writes
retain actor and previous/selected protected identities in append-only history;
clearing or choosing legacy content clears the content choice explicitly.
The uniform content resolver honors this choice and manual overrides. Legacy
project readers report an unavailable content preference rather than silently
substituting music; full project contract activation remains open WP-54/55 work.
Sixteen targeted preference, legacy edition and uniform resolver tests passed.
No historical export payloads were rewritten. UI and complete project resolution
acceptance remain pending. Native Windows publication remains disabled.

## Content export selection UI — 2026-11-26

WP-54/55 remain in progress. A German, authenticated and CSRF-protected selection
screen exposes the signed schema-2 content export service from the output library.
Selection checks do not approve music; explicit generation authorization pins
already confirmed content. Original context links, source indices, bounds and
orientation are shown. Two Django client tests passed: login/CSRF enforcement,
no generation on inspection, idempotent explicit authorization and stale rejection.
A synthetic real-browser test now covers signed selection, tampered-token rejection
and idempotent authorization; execution remains pending CI because Node is absent
locally. Review follow-ups make confirmation receipt selection deterministic and
classify out-of-range logical pages as INVALID_PAGE. Nine targeted PDF/pin/view
tests passed before the additional deterministic-receipt assertion. Project
resolver/preferences and neutral compound-source publication remain open.
Native Windows writes remain disabled.

## Content export activation — 2026-11-26

WP-54/55 remain **in progress**. A service-level content export path now binds
the explicitly selected confirmed editions, order, actor and output variant to
a signed preflight receipt. Authorization rechecks current eligibility under a
short SQLite writer lock and queues the existing durable generation worker.
Schema-2 archive-note generation reads only protected historical content pins;
later logical revisions do not rewrite an authorized run. Its artifact manifest
records the exact ordered content lineage. Legacy schema-1 generation is unchanged.

The export/snapshot regression set passed 26 tests with one POSIX-only worker
publication test skipped on Windows. After bounded selection, title revalidation
and aggregate output-limit hardening, 12 targeted authorization/pin/traceability
tests passed. Ruff, Django checks and migration drift checks passed. The synthetic
POSIX worker acceptance remains pending CI; no local Windows writable acceptance
or NAS/production operation has been performed.
Product UI, shared project selection/preferences and neutral compound publication
remain open. This service implementation is not completion of either package.

## Versioned content snapshot inputs — 2026-11-26

- WP-54/55 remain in progress. The additive continuation pins exact content
  confirmations, immutable occurrence order, source hashes, geometry and file
  revisions under `confirmed-content-inputs-v1`. Current authorization capture
  verifies bytes outside the short SQLite writer transaction and rechecks eligibility.
- Historical readers validate the retained confirmation and exact relational
  inputs without selecting a newer logical-page or edition revision. An additive
  snapshot input table preserves legacy assignment pins and payload readers.
  SQLite guards reject changes to referenced publication identity and content pins.
- Three targeted synthetic tests passed: historical parity after new-use
  invalidation, payload tampering and protected snapshot/file identities. Product
  authorization endpoints, durable generation and compound publication remain
  open; this is not completed WP-54/55 or a deployment/migration authorization.

## Explicit logical-page rendering — 2026-11-26

- WP-54/55 remain in progress. The separate rendering continuation adds a bounded
  isolated-parser primitive for explicitly ordered page/rectangle occurrences.
  It preserves vector graphics, original source bytes, physical-point CropBox
  offsets and UserUnit, with explicit quarter-turn orientation. No dimensions
  trigger splitting; native A3 remains one page unless explicit regions are supplied.
- Four targeted synthetic tests passed locally: native A3, repeated/multi-source
  ordering, rotation and units, invalid bounds, nonzero crop origins and fail-closed
  visible annotations. This is a derivative primitive, not CLEAN publication or
  musical approval. Product authorization, relational snapshot pins and generation
   integration are still open. The PDF/print/traceability regression run passed
   78 tests with one platform skip. A read-only bridge now verifies exact published
   bytes, renders currently confirmed content and rechecks eligibility before
   returning; three integration tests passed, including revision changes during
   rendering. Legacy whole-document editions retain their existing input semantics.
- This continuation starts from PR #65's `db216da0a2af114bc5af682531b46b33ba5e80a0`.
  It does not change native Windows writable acceptance or authorize deployment.
PR #66 CI on `8de0257b1091cb0c057df2e787f789927b1c2764` rejected two
rendering fixtures because their POSIX scratch directories were not private.
Fixtures now create mode `0700`; parser safeguards remain unchanged. Five
targeted rendering and browser-isolation tests passed locally. POSIX acceptance
and exact renewed CI remain pending.
## Collection review corrections — 2026-11-26

Independent review identified mixed relationship semantics and inaccurate local
override provenance. Containment cycle checks now traverse only movement/medley
edges; reciprocal explicit related-edition links are allowed and require active
arrangements. New `collection-metadata-v2` receipts identify the immutable
membership UUID/revision for local values; existing receipts are not rewritten.
Five targeted collection, isolated SQLite restore and backfill tests passed.
Membership positions remain deliberately zero-based, matching source/content
sequence conventions; original song numbers are separate human metadata.
Withdrawal/correction services remain an open WP-55 product task, not permission
to delete retained history. SQLite is the supported persistence target.

PR #65's preceding exact head
`8dddc58a7de4e2843eec3379d3262d6b766f7fb6` passed Foundation, Container
and Windows. The review correction requires its own exact-head gate.

## Native inventory correction — 2026-11-26

PR #65 Windows CI on `567eda5d87576ea0aa5f6fac76c7b606dd6bc11e`
failed to detect an added directory entry. Native directory timestamps alone
are insufficient: inventory now compares a bounded-memory, order-independent
SHA-256 name accumulator before and after enumeration, alongside the existing
handle fingerprint. Three targeted tests passed, including unchanged metadata
and equal-count name replacement. RAW access remains read-only and native
Windows publication remains disabled. Exact updated-head CI is pending.

## Browser isolation correction — 2026-11-26

PR #65 CI on `8846a1967cfd4b922b5b61b0f87251777d50a9c6` failed in
the browser gate: immutable DELETE triggers prevented disposable test DB flush
because their teardown fixture was scoped only to `tests/`. The fixture is now
root-scoped, retaining guards during every test and removing only DELETE guards
before transactional test teardown. Production migrations remain unchanged.
Ten targeted browser-directory isolation, migration and geometry tests passed;
the two browser-directory cases need no Node and verify guards plus clean state
across consecutive transactions. Exact-head CI must pass before integration.

Concise status per work package (IMPLEMENTATION_PLAN.md section 6). All work
packages were **Planned** at specification revision 2.0; statuses below
reflect actual completed work only.

## OpenCode integration evidence — 2026-11-26

PR #64 merged at `447a70acc332310f62b3c55aba572a34291ff6cd`;
exact Main CI `45846091525` passed Foundation, Container and Windows.
PR #63 passed the reviewed reconciliation head
`995bc403c3ec4199f1596849648366826d7272ad` and merged at
`d87a9e525463c6c786f018e9ebf79ec9e9a1d8c5`. Its exact Main CI
`45850641258` passed Foundation, Container and Windows.

Independent Qwen review of the committed content foundation found no blockers
in its bounded persistence scope. Different/inactive confirmation actors are
tested; published-byte verification now follows the supplied/model DB alias.
The intended content-only approval scope does not approve an entire BASE file.
Twenty-five targeted edition, confirmation and compatibility tests passed after
the alias adjustment. The prior exact foundation full suite passed 1,308 tests,
skipped 147 and failed two Windows symlink fixtures with `WinError 1314`;
this is an environment-limited failing gate, not a successful full suite.

## OpenCode content foundation — 2026-11-26

WP-54/55 are **in progress**, not complete or enabled for product export.
The additive implementation introduces stable document identities, immutable
region and logical-page revisions, ordered occurrence manifests, explicit visual
inspection and confirmation, and a read-only whole-file compatibility adapter.
Changes to relevant geometry or ordering exclude affected content from new use;
previous confirmations and legacy assignments remain retained. SQLite history
guards cover the new records. Native Windows storage writes remain disabled.

Collections, ordered membership, alternative titles and typed composition/edition
relationships are distinct from filename/title identity. Membership snapshots
retain effective metadata and its collection/work/local provenance. Synthetic
tests exercise 125 independent repeated-title works and cycle rejection for a
Deutsche Messe hierarchy. Twenty-four targeted confirmation, compatibility,
uniform selection and existing edition tests passed. Partial content confirmation
can span separately published unconfirmed BASE copies without approving either
whole file. Independent logical revisions retain unrelated confirmed content.
An isolated synthetic SQLite backup preserved identities, metadata provenance,
integrity, foreign keys and history guards; this is not installation recovery.

Current-schema ingestion also materializes the stable document bridge. Serialized
logical-page append operations reject stale and non-integer revision tokens.
Seventeen targeted confirmation, geometry and indexing tests passed locally;
fourteen POSIX indexing cases were skipped on Windows. Local browser acceptance
could not start its Node subprocess: 22 failures and four skips. Node is absent
from the current environment; browser verification remains open, not waived.

Shared project resolver/preference and generation integration, neutral compound
publication, complete backup/restore acceptance and full delivery verification
remain open. Schema rollback/rebuild tests are not physical power-loss or NAS
acceptance. No actual association data or production migration was used.

## Codex to OpenCode checkpoint — 2026-11-26

PR #62 merged at `5f99344e803b14f9a2ab77bbb298e4edf9810204`. Exact post-merge
Main CI `45834711455` passed Foundation, Container, and Windows. The merged
PR head `97a9d9e8e67cc16d965bd133b91aedf874e6a6ab` passed exact PR CI
`45831584098` after a stale export cleanup test fixture was corrected.

WP-06p POSIX exact CLEAN reconstruction is implemented in open draft PR #64.
Exact CI `45833447636` passed at implementation checkpoint
`b4a571d0b92e4a0a7b09f0fad52e4f417af68303`. The transfer adds only this progress
record and the handoff snapshot. The new head needs its own exact CI. Native
Windows writable storage and independent OS RAW-denial acceptance remain open.

WP-54 stable source-page identity, repeatable legacy backfill, and original
CropBox capture for new indexing are implemented in open draft PR #63. Exact
CI `45831729109` passed at `1cde38a59b51bbd2cbf55f0345a344d10e6a0d6d`. WP-54
region/logical-page and content references, the confirmed whole-file adapter,
and compatibility acceptance remain in progress. WP-55 remains planned.

Both drafts target `main`. Continue the reviewed exact-head integration gates
and verify exact Main CI after each merge. Continue WP-54 and WP-55 according
to their dependencies with remaining Windows acceptance tracked separately.
See `docs/HANDOFF.md` for complete refs, evidence, and recovery material.

## Codex continuation — 2026-11-26

### WP-54 source-page checkpoint

Stable page UUIDs identify zero-based pages within exact source versions.
The additive migrations retain existing validation, archive assignments,
preferences and snapshot records. Per-version backfill transactions can be
rerun and verify previously written rows. Legacy pages retain their effective
geometry with an explicitly unknown original CropBox. New validation records
original and effective geometry from the same isolated parser invocation.
Source geometry fingerprints distinguish those evidence scopes. This increment
does not activate regions or change the legacy resolver. Logical-page, region,
content-reference and compatibility migration acceptance remain in progress.

Focused verification passed on Windows for archive models, page migrations and
geometry, with no migration drift. Ubuntu verified synthetic new indexing and
idempotent same-hash reindexing. The migration tests exercised schema rollback
and deterministic rebuild with no production data.

### WP-06p explicit CLEAN reconstruction checkpoint

`python manage.py restore_clean_copy <archive-file-uuid>` queues restoration at
one missing acknowledged CLEAN path. The existing archive worker can use an
exact verified historical CLEAN publication or fall back to the pinned RAW
version. It stages a physically independent copy and uses the existing
no-clobber publication and durable operation intent. The original publication
receipt, confirmation, and logical revision remain pinned. An occupied path
or absent ownership proof cannot authorize replacement or acknowledgement.
Windows writes remain disabled. This command runs through the normal configured
worker and is separate from backup restore.

Seven synthetic Ubuntu restoration tests passed, including real worker exits
after the link and after acknowledgement, loss of proof, changed RAW, and a
racing target. The shared Windows lifecycle, publication and ownership suites
passed 57 tests. Ruff, migration drift, and diff whitespace checks passed.

### WP-06p shared storage checkpoint

Verified and fast-forwarded the clean checkout to the remote handoff SHA
`b5fecb12233a8782e1e5c59480a5d1d9605dafa7` with the required transfer trailer.
The comparison base remains `ab172f6f942d5de743aec21aa6f0222caaa9798e`.

WP-06p remains in progress. The shared PDF processor verifies each physical
scratch copy's SHA-256 before launching the parser and retains the workspace if
termination is unproven. Archive publication and indexing use the existing
worker recovery hook for parser scratch. Cleanup preserves marked workspaces
after an abrupt parser interruption until child termination can be established.
Unknown files are preserved and disposable cleanup failures warn. Publication
still checks final name spelling through the pinned target parent. Publication
and metadata durability boundaries are retained. Windows writes remain disabled.

Reindexing the same source version records a missing or corrupt acknowledged
CLEAN copy as unavailable without changing its approval, path or receipt.
Repeated scans and ordinary copy requests preserve that publication for
reconciliation rather than creating a replacement at a different path. A scan
restores availability after exact bytes reappear at the recorded path, with
size, SHA-256 and receipt verification and the logical revision retained for
historical export pins. This check runs when indexing rediscovers the same RAW
version. Direct recovery of historical copies without that RAW version and
automatic reconstruction of missing bytes remain open.

Focused checks: 75 Windows PDF/publication-contract tests passed with one POSIX
permissions test skipped. Six final Ubuntu parser cleanup and confirmed CLEAN
loss/restore cases passed. The geometry suites passed 118 tests. Ruff lint and
format, Django system check, migration drift, and diff whitespace checks passed.

WP-54 preparation now accepts fractional CropBox offsets with non-integer
UserUnit across the four page orientations. The additive source/content migration
and WP-55 work remain pending. The next storage increment is exact-path
reconciliation of acknowledged missing CLEAN results, while preserving the
receipt, confirmed history and existing bytes on any unsafe or conflicting path.

## OpenCode continuation — 2026-11-26

### Owner amendment and final Codex transfer

DEC-15 authorizes recoverability-based external publication and isolated processing
scratch. It supersedes the earlier unconditional parent-namespace/permanent-stage-
deletion durability blocker, not RAW denial, authoritative DB/history, hash identity,
no-clobber, confirmation or path/security guarantees. The old blocker entries below
are historical analysis under DEC-14, not current release criteria. It was a missing
platform-contract guarantee, not an observed lost publication or power-loss test.
Windows writes and production RAW certification remain unavailable; workspace,
isolated-input and acknowledged-file reconciliation obligations remain implementation
and verification work. WP-54/55 may proceed on verified shared interfaces/supported
backends without waiting for complete Windows production acceptance or packaging.

Documentation-only owner task: no further implementation, permissions, migrations,
merge or deployment. All continuation commits since comparison base
`ab172f6f942d5de743aec21aa6f0222caaa9798e` and their diffs were reviewed; intended
implementation and recovery branches are preserved. Before this update remote/local
HEAD was `65c94e1155b88fe86a197e42f9ed601be513c747`, worktree clean, PR #62 open
and draft. Its Foundation, Container and Windows checks were observed completed
SUCCESS (run 45815589039); exact deterministic CI was already verified at
`d5460588c999251e5f98a4184538528029ddbaeb`. These are prior-SHA results, not
claims about the final documentation/transfer HEAD. See HANDOFF for the final
snapshot and precise next action. No expensive regression repeated for this task.

Execution: Sol supplied bounded read-only architecture consistency analysis;
coordinator integrated the authorized requirements/decision/dependency changes
and transfer documents; Qwen independently reviewed requirements/acceptance
consistency: passed, no blocking contradictions or omissions.
Documentation checks: `scripts/check_requirements.py` passed (119 canonical IDs,
61 aliases, zero errors); structural traceability tests passed (5); Git whitespace
check passed. Existing implementation evidence reused; no full suite repeated.

The remote takeover gate passed at
`dd336089fa15b23a377540b5cfae4a472cd25237` on
`codex/windows-source-reader`; the preserved source-reader increment was reviewed
against the recorded main base. Implementation continues on that branch.

Publication, durable verification and retained-stage cleanup now dispatch through
backend-owned operations rather than POSIX descriptors in shared policy. The
POSIX implementation retains no-clobber linking, identity checks and directory
flushes. New shared contracts cover policy rejection before effects, retained
identity and durable acknowledgement. Fourteen targeted publication/inventory/
backup-contract tests passed locally; Ruff lint/format and the five structural
traceability tests passed. The requirements checker reports 119 definitions,
61 aliases and no errors.

The source/inventory targeted rerun passed 17 tests; two native tests failed at
synthetic symlink setup with Windows error 1314 (missing privilege), before their
security assertions. Assertions were not weakened or skipped. The first full
regression exceeded its 120-second command limit and was terminated, not verified.
The replacement full Windows regression completed in 1228.43 seconds: 942 passed,
143 skipped and two failed at the same symlink setup privilege boundary. This is
not a green full regression. The run started before the additional junction cases;
those have separate targeted evidence. PR #62 exact-head CI passed for
`d299efe18328f25e1b1ece896253099eaca542e8`: Foundation, Container and Windows
shared-runtime checks succeeded. This evidence covers that commit only, not
subsequent changes. The previous wait for `7bf5425` correctly rejected a changed
PR head; it is not successful verification.
Two additional actual Windows junction tests passed without symlink privilege:
reparse leaves/ancestors and replacement of a child directory cannot redirect a
source read. They supplement the unchanged symlink cases, not replace them.
Native writable storage, independent RAW protection and the rest of WP-06p remain
in progress; no merge, deployment or real-data operation is claimed.

Execution: the coordinator implemented the backend-boundary refactor and junction
tests directly before delegation was requested. Sol completed a read-only native
storage security investigation without mutations or repeated verification. The
reviewed API contracts do not yet establish a complete non-admin namespace barrier
for the current retained-hardlink protocol. Qwen implemented shared failure tests;
Sol's independent review found erased mock history and test-owned ordering claims.
Qwen partly corrected them before reaching its execution step limit. Sol completed
the fixes and added an actual worker regression: post-mutation failure retains
PENDING proof and REVIEW_REQUIRED/OPERATION_UNCERTAIN, without acknowledgement or
blind retry. The coordinator reviewed the corrected diff. The two targeted files
passed 35 tests; touched-file Ruff lint/format and whitespace checks passed. These
are policy/lifecycle contracts, not native power-loss durability evidence.
Sol then moved retained-stage proof validation behind the backend interface,
preserving the exact POSIX regular-file, identity and two-link checks. Shared
verification still checks bytes first and proof before inspection/durability.
Publication contracts, lifecycle, archive-file and marker-file tests passed
45 cases with 25 platform skips on Windows; touched-file Ruff and whitespace
checks passed. The coordinator reviewed the dispatch and proof-test diff.
Sol also encapsulated the unchanged effective-UID stage ownership check in the
backend. Archive cleanup and both export cleanup paths validate ownership before
identity-checked discard. Twelve focused tests passed with 39 POSIX/platform
skips on Windows; Ruff and whitespace checks passed. Consumer tests use metadata
without POSIX ownership fields and reject ownership/metadata failures before
discard. Linux integration coverage remains required; native Windows ownership
enforcement is not implemented by this extraction.
DEC-14 records the approved dedicated-identity target and bounded
alternative persistence/recovery design authority; Windows writes remain disabled.

Sol added a read-only current-process Windows token evidence adapter and 51
passing targeted tests, including native TOKEN_QUERY smoke. Native fixed-size
elevation-query behavior required an implementation correction and dedicated
regressions. The adapter retains no certification of RAW isolation/publication;
it does not inspect RAW ACLs, thread impersonation or child-process identities.
Touched-file Ruff and whitespace checks passed. Qwen independently reviewed the
adapter and proof extraction. Sol added group-attribute, array-boundary and
privilege-query regressions and sanitized native buffer/argument failures.
The proposed group-mask change was rejected against Microsoft's TOKEN_GROUPS
contract: enabled is bit 4, not enabled-by-default bit 2. No RAW isolation or
durability is certified.
The proof/ownership checkpoint was pushed as `1578767`; no merge is claimed.

Sol added a separate pinned-root security-descriptor evidence adapter: 26 tests
passed, including native synthetic-root acceptance. The existing source handle
fails closed without READ_CONTROL; a test-only handle proves the query path without
reopening production paths or changing source access. Descriptor snapshots do not
verify effective access, descendants or persistent RAW enforcement. Ruff and
whitespace checks passed. Qwen's proposed LocalFree/ACL-class corrections were
rejected against Microsoft's primary contracts: NULL means successful LocalFree,
and AclSizeInformation is 2. Both query adapters now preserve existing FileError
codes before sanitizing native decoding errors. The final combined targeted run
passed 80 tests, including both actual native smoke paths. Descriptor input is
OS-produced and validated, not an arbitrary-buffer parser. No provisioning occurred.
The combined evidence checkpoint was pushed as
`9aa26de069d6ded438ea5f2b93cb51321526f6a8`. Its exact-head PR #62 CI passed
Foundation, Container and Windows shared-runtime checks. Qwen explicitly retracted
the incorrect API findings; no blocking findings remain in this increment. WP-06p
is incomplete and the PR remains draft; no merge or deployment is claimed.

Sol integrated explicit optional `inspect_security=True` initial root/ancestor
pinning with READ_CONTROL. Default access, source-stream rights and no-delete
sharing are unchanged; there is no later pathname reopen or startup/factory
enabling. Native descriptor acceptance now uses the public mode. Focused source
and root-security tests passed 47 cases, with only the two previously recorded
privileged symlink-setup cases explicitly deselected; assertions remain unchanged.
Ruff and whitespace checks passed. Qwen's independent delta review found no
blocking findings; initial pins still use OPEN_EXISTING (3), not creation.
This increment provides inspectable descriptors, not RAW isolation certification.

Sol added root-directory AccessCheck evidence using a query-only DuplicateTokenEx
token and independently owned owner/group/DACL descriptor allocation. Thirty-nine
targeted tests passed, including native read-only synthetic-root acceptance;
Ruff and whitespace checks passed. Buffer limits, denial versus API failure,
mutation rights, ownership/token risks and resource cleanup are covered. Qwen's
independent review found no blockers. Its suggested mutation-mask change was
rejected: 0x0116 excludes read-data (1) and read-EA (8); the existing mask is correct.
Seven additional mask/pure-read grant regressions passed; the final AccessCheck
targeted file passed 46 tests, with clean Ruff and whitespace checks. Files/descendants,
parent-entry rights, configured dedicated
identity and process/thread enforcement remain unimplemented; capabilities remain
uncertified. The optional pinning checkpoint was pushed as `624ae5d`; exact CI
success still applies to `9aa26de`, not this later checkpoint.
The subsequent AccessCheck checkpoint
`5628046caaffdc736c88b1d8571fb672166584d0` passed exact-head PR #62 Foundation,
Container and Windows shared-runtime CI. This also covers the optional pinning
increment. WP-06p remains incomplete and the PR remains draft.

Sol added explicit-mode context-scoped single-entry security pins and retained
initial-parent evidence, with file/directory-specific AccessCheck mutation masks.
Native focused source/access tests passed 72 cases, with exactly the two known
privileged symlink-setup cases deselected and unchanged. Native coverage includes
file/directory/parent evidence, disabled-mode and drive-root refusal, junction and
hardlink rejection, and failed-query pin cleanup. Ruff and whitespace checks passed;
Qwen's independent delta review found no blockers. Carried mask/Python-version
claims were rejected: the mask excludes READ_DATA and Path.hardlink_to is supported
by the pinned Python 3.12 runtime. Initial opens remain OPEN_EXISTING (3).
This does not certify recursive RAW protection,
configured identity or stable ACL enforcement. No provisioning or write enabling
occurred.

Sol added bounded recursive RAW evidence aggregation with expected-user identity
comparison, root/parent/descendant checks and aggregate-only reporting. Thirty-five
tests passed, including native nested synthetic traversal with honest mutation
rejection. Limits, cancellation, query failures, unsafe entries, disappearing or
changed identities, directory mutation and cycles return incomplete reports;
completed rejected inventories are distinct. Ruff and whitespace checks passed.
Qwen's independent review found no blocking findings. No atomic/persistent ACL enforcement or process-role
certification is claimed. The descendant checkpoint was pushed as `0f342a8`; the
latest exact CI evidence remains `5628046`.

Independent preparatory WP-54 work: Sol added pure immutable page/rectangle
geometry and invertible display transforms without parser, model, migration or
workflow activation. Seventy-nine targeted tests passed; Ruff and whitespace checks
passed. Input boxes retain default-user-space coordinates and original CropBox;
canonical regions use physical PDF points after UserUnit conversion. Fingerprints
include original/effective geometry and schema. Invalid or outside regions fail
closed without clipping. Qwen's independent review found no blockers; a possible
floating-point endpoint rejection was reproduced and corrected by mapping exact UI
edges to exact PDF edges, without clipping interior points or widening containment.
The final targeted geometry run passed 91 tests with clean Ruff and whitespace checks.
The coordinator reviewed the endpoint mapping. Future parser
wiring must preserve the original CropBox, currently lost by PageInfo's effective
crop normalization. WP-54 remains planned:
WP-06p, additive migration, legacy compatibility and acceptance gates are unchanged.

The combined recursive-evidence/pure-geometry checkpoint
`5db72d4ac4d34ef1df397570a93f8ff2e4871977` passed exact-head PR #62
Foundation, Container and Windows shared-runtime CI. The worktree was clean at
verification. No merge is claimed: WP-06p remains incomplete, Windows writes stay
disabled, and WP-54 geometry is preparatory rather than activated product behavior.

Sol added opt-in lossless parser evidence and an explicit page-geometry bridge.
Original CropBox is retained separately; legacy PageInfo fields, effective crop,
inspection IPC and manifest serialization remain unchanged. Legacy metadata cannot
invent original geometry, and inconsistent evidence fails closed. Source-geometry
and geometry suites passed 114 tests, including actual isolated inspection IPC
parity; Ruff and whitespace checks passed. Qwen's independent delta review found
no findings; the coordinator reviewed the implementation and compatibility tests.
No model, migration, source-version binding or production IPC activation is added.

The opt-in source-geometry checkpoint
`d5460588c999251e5f98a4184538528029ddbaeb` passed exact-head PR #62
Foundation, Container and Windows shared-runtime CI. Sol then evaluated the
specific same-volume write-through move candidate without mutations. Microsoft's
MoveFileExW contract supports persistence of the move itself; its copy/delete
example is not an exclusive restriction. Two preverified independent files and
operation-bound distinct identities could preserve atomic final visibility and
short publication transactions. However, the reviewed contracts do not establish
durability of separately created ancestor chains or later identity-checked recovery
copy deletion. WP-06p is blocked on that narrow platform-contract limitation, not
on missing general design authorization. Windows writes remain disabled; PR #62
remains draft. Next action: obtain authoritative platform evidence for those
namespace barriers or an owner decision on a separately reviewed alternative.
No external support contact, infrastructure change or hardware test was performed.

## Autonomous continuation — 2026-11-25

### Current requirements checkpoint

Verified baseline: PR #61 passed exact-head CI 45691065700, merged at
`ab172f6f942d5de743aec21aa6f0222caaa9798e`, and exact Main CI 45694893160
passed all four jobs. DEC-13 is approved; the incomplete OCR draft remains in
the recorded local stash. Existing work is preserved.

`codex/windows-source-reader` implements the next cohesive WP-06p increment:
local NTFS source handles with native identity/time metadata, shared source-root
selection and removal of remaining root-descriptor/parent details from archive
and export services. Thirteen actual native tests passed. Seventy-three targeted
configuration/runtime/source tests passed before the additional timestamp oracle;
the final native suite includes that oracle. An initial root-reentry regression
exposed insufficient attribute-only sharing locks; READ_DATA/LIST_DIRECTORY rights
fixed the cause and the unchanged rename assertion now passes. Ruff lint/format,
Actionlint and Django system/migration-drift checks passed. Full regression is
running; exact-head Linux/Windows/Container and integration gates remain pending.
Native writes, independent process-wide RAW denial and desktop acceptance remain
open. No new dependency, real-data migration, release or NAS operation was added.

### Earlier runtime-proof checkpoint

PR #60 passed exact-head CI 45684801969 at
`4f4434d2e31c3f69f0e644376fc6ac14f3e781ed` and merged at
`7df8901545c55709b3959f818cddfd9ff8a2f6e6`. Review gates were clean with no
submitted reviews or unresolved threads. Exact Main CI 45687344097 passed all
four jobs on that merge SHA.
PR #59's exact Main CI 45681642452 passed at its recorded merge SHA.

The next cohesive increment `codex/portable-runtime-proof` turns the successful
Windows lifecycle experiment into a reusable synthetic tool and subprocess
regression: actual initialization, exclusive ownership, loopback auth/CSRF,
managed web/worker shutdown and isolated SQLite restore. Twelve targeted
startup/worker/runtime tests passed on Windows. Ruff lint/format passed.
Full local regression passed (934 tests, 140 platform skips). The unchanged
application's browser evidence is reused from PR #60 (22 passed, four POSIX
skips); required CI still exercises its own browser/container gates. Actionlint,
Django system/migration-drift and structural traceability checks passed.
Final exact-head Linux/Windows CI remains pending.
The tool never accepts existing installation paths and ignores inherited
application configuration; the production desktop launcher/native writable
backend remain unimplemented. DEC-13 is approved; portability still comes first.

The complete requirements consolidation (including Appendix A) is integrated by
PR #58 at `d468df829d5db4d41c90936065309ed3abd14313`. Exact Main CI
45674600196 passed Foundation, Container, Windows shared runtime and changes.
The canonical register contains 119 requirements and the crosswalk 61 source
aliases. The owner explicitly approved DEC-13 as proposed on 2026-11-25:
additive content/region architecture, revision-bound inspection, protected legacy
compatibility and expanded core templates with duplex/cut/fold. Secondary and
deferred priorities remain unchanged. Portability completion still comes first.

PR #59 passed exact-head CI 45677648319 at
`7393829567ea0df4d53567a4f8e7c53581789335` and merged at
`572ab2b305da228b69eee5b553357299b5845b79`. Its exact Main waiter is active;
no Main success is claimed until that operation returns success.

The cohesive follow-up `codex/portable-filesystem-boundaries` isolates STATUS
metadata/replacement, private scratch-directory creation and backup traversal
behind the existing filesystem boundary. Backup traversal retains limits and
exclusions, checks reopened identities and rejects directory mutation. Proven
pre-publication conflicts remain distinct from uncertain replacement/flush
failures. Relative local-profile storage/runtime paths are pinned at startup.
The native Windows writable backend and desktop/runtime gates remain open.

Focused Windows configuration and portable inventory checks passed (55 tests).
Full local regression passed (933 tests, 140 platform skips), and browser
acceptance passed (22 tests, four POSIX skips). Marker/private-directory POSIX
tests await Linux CI. Ruff lint/format, Actionlint, Django system/migration-drift
and structural traceability checks passed. The first browser attempt failed
because NODE_PATH was absent after the runtime change; the unchanged suite
passed with the existing bundled Playwright 1.62.1 and Edge.
No new dependency, product-model change, real-data or NAS operation was added.

### Prior initialization and consolidation checkpoints

Unaffected WP-06p continuation is on `codex/portable-runtime-roots`, based on
requirements commit `61cbe8d05ef7e1bfb6882f5628a94fdeaabde035` in PR #58.
The documentation PR keeps its existing exact-SHA waiter.
Focused commit `2585645` moves local initialization path validation ahead of
secret creation. The same increment adds link/reparse and runtime hardlink guards.
Forty-six targeted Windows configuration checks passed. The two sandbox hardlink
setup failures were recovered by running the unchanged tests with approved native
access. Ruff lint/format and whitespace checks passed.
The full local regression at the link-guard checkpoint passed with 921 tests and
133 platform skips. Subsequent fixed-error and Windows-namespace changes passed
53 focused configuration tests. Separate browser acceptance on the final guard
implementation passed with 22 tests and four POSIX skips. Django system and
migration drift checks passed. Final exact-head CI and integration remain pending.

Native Windows storage, independent RAW denial, supervised desktop/runtime proof
and packaged acceptance remain separate open gates. The configuration guards
do not complete WP-06p. DEC-13 remains the consolidated decision for expanded
content/region/layout implementation; consistent portability work continues.

The owner supplied the complete extended specification including Appendix A.
Consolidation is in progress on `codex/requirements-rebaseline` from verified main
`ca8647cfb04d26e3d61048e22e8885e6b5c460bb`.
PR #57 merged at that SHA; exact Main CI 45640472935 passed Foundation, Container,
Windows shared runtime and changes. PR #56's Main CI 45633095503 also passed.
There were no open PRs at the rebaseline inspection.

Requirements revision 3 and its source-alias crosswalk preserve EXT-01–18,
FUT-01–07, REF-01–36 and unnumbered clauses. Architecture and WPs are rebaselined
for source/page/region/content independence, safe additive compatibility,
collections/movements and template-driven layout. New acceptance is planned,
not retrospectively verified by old test names. DEC-13 records one material
content-model/confirmation/layout implementation decision. Existing consistent
development autonomy continues and WP-06p portability completion remains first.

The incomplete file-heading OCR draft and dependency changes were preserved in
local Git stash `d36f3b56e06cdfbf3a1f26950e6950fe6059f0c0` from
`codex/ocr-workflow`. It is unintegrated, unverified, has no registered product
entry point and is not a remote transfer artifact. Reassess it after content/
region contracts. Do not restore it over the requirements branch or claim WP-24
implemented. Source, test and private data were not discarded.

The tool runtime update removed the earlier bundled Python location. The existing
local venv was rebound to the new bundled Python 3.12.14 using uv --allow-existing;
locked offline sync passed. The lost Main waiter had no surviving process/result.
Its bounded replacement verified the same exact merge SHA without rerunning CI.
The ignored successful commit-message file was removed under the latest AGENTS rule.

Next actions are to validate/integrate this single coherent consolidation boundary,
continue unaffected WP-06p, and obtain DEC-13 before expanded content migrations
or file-level OCR implementation that would cement superseded assumptions.
The structural checker reports 119 unique canonical requirement definitions and
61 source aliases without missing/duplicate IDs, WPs, headings or evidence paths.
Its five regressions and two existing workflow contract tests passed. Ruff
lint/format and whitespace review passed. Application behavior is unchanged, so
the verified baseline suites are reused locally. Required exact-head CI and
post-merge Main CI remain separate integration gates.

PR #56 integrated the first shared-runtime increment at
`f158db807bb296a4ee445faa2eaeb3ec8312c54e`. Exact-head PR CI
`45628909037` passed Foundation, Container, changes and Windows runtime checks.
Post-merge Main CI `45633095503` has one active SHA-bound waiter.
The cohesive follow-up on `codex/portable-storage-runtime` is in progress.
It moves inventory enumeration into the filesystem boundary, retaining
directory mutation checks and platform-independent inventory policy.
Two portable contract tests pass on Windows; three actual POSIX inventory
tests remain for Linux verification. Updated delivery-package/tool-first
instructions accompany this functional increment in PROCESS.md.
The same increment consolidates bounded exclusive staging writes for archive
copies and generated PDFs in the filesystem boundary. Focused Windows checks
passed with 16 tests and 22 POSIX skips. New Linux staging tests cover empty and
oversized input, producer failure cleanup and preservation of existing bytes.
Full local Windows Python verification passed with 906 tests and 133 platform
skips. Separate browser verification passed with 22 tests and four POSIX skips.
Ruff, Actionlint and Django system/migration checks passed. Full package diff
reviewed. PR Linux/Container and integration verification remain pending.

The owner accepted takeover and authorized controlled P0 integration at
`b9e9e9d84818fcdb006933d016fa02863c4b2db5`. PR #55 merged at
`cca4fa9bd4026f2d7361459280cab5136c2aacb3`. Exact post-merge Main CI
`45621767958` passed Foundation, Container and changes at that exact SHA.
The original wait was interrupted with the chat; its controlled replacement
completed with exit 0 and compact local evidence under `.dev/ci-wait/`.
Portability work is in progress on `codex/portability-foundation`.
The owner authorized compliant package implementation and merges through product
completion, with portability preceding WP-24. Physical acceptance and deployment
retain separate authorization gates.

The first portability increment removes working-directory assumptions in PDF
children and migration checks, adds Windows runtime CI and records distribution
requirements, packaging choices and outstanding native storage contracts.
Two focused Windows regressions, locked environment sync, Ruff and Django
system/migration checks passed. Full local Windows regression passed with
904 tests and 129 platform skips. Actionlint and both workflow contract tests
passed. Separate Windows browser acceptance passed with 22 tests and four
POSIX skips. PR CI and integration of this increment remain pending.
The first local suite produced no terminal result and was terminated without
a success claim. Its verbose replacement identified a Windows socketpair
accept blocked inside the sandbox in test_gateway.py. The full suite was
restarted with approved loopback access and a 120-second stack diagnostic.
Installed Windows distribution, native archive publication and NAS acceptance
remain outstanding. Earlier transfer entries below describe historical snapshots.

## Current transfer summary — 2026-11-25

- Latest snapshot: `docs/HANDOFF.md`; branch `fix/ci-waiter-p0`, PR #55 open.
  Compare all work from verified main `0d24dae03711254e48a0c167c36ff44a74de4600`
  (PR #54, Main CI `45574328173` success). Reported earlier main `3dc3eb4…`
  (PR #53/Main CI `45512749289`) is superseded only by release-evidence docs.
- PR #53 completed governance consolidation and deterministic SHA-bound waiting
  (DEC-11, PROCESS, standard-checks, existing waiter); no gates/permissions weakened.
- Current software integration includes WP-33c/d, WP-36a/b, WP-37a–c, WP-38a/b,
  WP-39 (PR #50, `fd0ed9ce0b4efeb05c7210f237dcb7896c38a31a`) and current-feature
  synthetic web/worker/TLS distribution PR #51/52. Older pending/preview rows below
  are historical, not current status. WP-47a software backup is complete; physical
  NAS/full operations remain separate. Release/digest evidence: RELEASES.md.
- No unfinished product implementation is being transferred. P0 implementation
  `fa675797c2f310ce476deaf4d3aebb402d23b585` is local-tested/pushed, not merged;
  explicit separate merge authorization remains required. Transfer docs do not
  authorize P1/P2, a new package, release or NAS use. Final marker CI is separate
  from implementation evidence and remains discoverable in exact-head PR checks.
- Remaining planned features: OCR/full integrity, scan enhancement, actual
  marchbook output and physical printing; NAS/quality/restore/load/license/product
  decisions remain as detailed in HANDOFF and DECISIONS. Recommend owner-approved
  WP-24 next after P0 integration; no implementation started here.

## Workflow efficiency P0 — CI waiter hardening (2026-11-25)

- Baseline `0d24dae03711254e48a0c167c36ff44a74de4600`; branch `fix/ci-waiter-p0`.
- Implemented non-removable Foundation/Container gates, verified cached exact-diff
  docs-only exception, strict SHA evidence, and individual run-job verification.
  Malformed, ambiguous and incomplete pages fail closed; no replacement waiter,
  product change, P1/P2, CI weakening or integration authorization change.
- Synthetic baseline reproduction: 11 failed / 6 passed; corrected targeted suite:
  78 passed. Ruff lint/format, lockfile, Django system and migration checks passed.
- Full local Python suite: 902 passed / 131 platform skips; browser suite:
  22 passed / 4 POSIX skips on Windows. Earlier outer timeouts were not successes.
  Final-head Linux CI remains a delivery gate; results recorded on PR.
  Not merged; separate explicit owner authorization is required for merge.

| WP | Scope | Status | Commit / PR | Test evidence | Blockers | Next |
| --- | --- | --- | --- | --- | --- | --- |
| WP-01 | Repository, development tooling and minimal CI | Verified | PR #1 merged (merge commit `bcdf272`) | Local checks (below) + GitHub Actions run 44694745130, job "Foundation (ruff + pytest)" success | None | WP-02 |
| WP-02 | Django skeleton and configuration | Verified | PR #2 merged (run 44724272495 success) | Local checks (below) + GitHub Actions run 44724272495, job "Foundation (ruff + pytest)" success | None | WP-03 |
| WP-03 | Authentication and session baseline | Merged, audited | PR #3, merge `245c258` | PR head `7cca167`, CI run 44738003509 passed; auth follow-ups merged with WP-03a | None | Complete |
| WP-03a | Application shell and navigation | Merged, CI verified | PR #4; merge `e913d706d869de14f2e063eb0fb8b2835d548e98` | 90 tests, Ruff lint/format, local Playwright and combined CI run 44747734412 passed | None | Complete |
| WP-04a | Technical logging and mode contract | Merged, CI verified | PR #5; merge `d4b2d2bcfdee21de0628a2141f995b0d49fd3441` | Windows unittest: 5 passed; Linux CI runs 44746685234 and 44747068821 passed | NAS acceptance outstanding | WP-04b |
| WP-04b | Authenticated debug UI | Merged, CI verified | PR #6; merge `ec705b29bc56d212cad1c34369cc5ba9dd9821c5` | 110 local tests, 2 Playwright tests; Linux CI run 44749299835 passed | NAS acceptance pending | WP-05a |
| WP-05a | Durable queue, claim and singleton worker | Merged, CI verified | PR #7; merge `5e6bacc816f69999bbe88eae11536cc2dee71da2` | 141 local tests, 2 browser tests; Linux CI 44757097570 passed | NAS acceptance pending | Recovery/UI integrated through WP-05b/05c; published preview remains web-only |
| WP-05b / WP-05c | Recovery, cancellation and job UI | Merged, CI verified | PR #11; merge `470e7c8b0421d91ae38fbc65b888c16e70b1088c` | 218 tests, 3 browser tests; final PR CI 44823906492 and main CI 44824237705 passed | None for software scope | WP-11/12 |
| WP-11 / WP-12 | Musical catalog and members | Merged, CI verified | PR #12, merge `a2d7264`; browser follow-up PR #13, merge `2f4b0e9` | 265 tests, four browsers; final main CI 44842489941 passed | None for software scope | Complete |
| WP-17 | Bounded PDF foundation | Merged, CI verified | PR #14, merge `c12e71c` | 319 Linux tests, four browsers; native image checks; main CI 44845475304 passed | NAS resource acceptance separate | Complete |
| WP-13 | Archive identities and state transitions | Merged, CI verified | PR #16, merge `a480a2a` | 373 Linux tests, four browsers; final PR CI 44881432325 / main CI 44881714517 passed; merged tree matched | NAS gate separate | WP-14 |
| WP-14 | Safe file publication | Merged, CI verified | PR #17, merge `5874c7c` | 424 Linux tests, four browsers; final PR CI 44887606153 and main CI 44897447951 passed; merged tree matched | NAS gate separate | WP-15/18/19 |
| WP-18 | Secure local PDF preview | Merged, CI verified | PR #18, merge `e04905a` | Main CI 44910769120 passed; combined WP-18/19 main CI 44943760201 passed | NAS gate separate | WP-20a |
| WP-19 | Filename/text-layer recognition | Merged, CI verified | PR #19, merge `8cedf7b` | PR CI 44939684382 and combined main CI 44943760201 passed | Local Windows queue timing failures remain recorded below | WP-15 |
| WP-15 | Indexing and separate STATUS | Merged, software verified | PR #21, merge `3a5a692` | Final PR CI 44954321633 and main CI 44956825128 passed; exact merged tree matched | Private NAS gates separate | Complete software scope |
| WP-16 | German indexing UI | Merged, software verified | PR #22, merge `4c75350` | 493 Linux tests, six browsers; final PR CI 44959000193 and main CI 44959464054 passed | Private NAS gates separate | Complete software scope |
| WP-20a | Individual review and publication | Merged, software verified | PR #23, merge `dc78924` | 505 Linux tests, seven browsers; final PR CI 44962136139 and main CI 44962643794 passed | Local Windows queue timing issue; private NAS gates separate | Complete software scope |
| WP-20b | Inspected batch approval and navigation | Merged, software verified | PR #24, merge `05a4898` | 520 Linux tests, eight browsers; final PR CI 44964388557 and main CI 44964905107 passed | Local Windows queue timing issue; private NAS gates separate | Complete software scope |
| WP-21 | Searchable library and independent completeness | Merged, software verified | PR #25, merge `eb6c542` | 530 Linux tests, nine browsers; final PR CI 44967842286 and main CI 44968360320 passed; exact merged tree matched | Private NAS gates and baseline Windows queue timing issue separate | Approved sequence complete; stop |
| WP-09 | Service-aware mount and startup validation | Merged, software verified | PR #8; merge `62d85b3` | 19 storage tests locally; actual Linux container/host negatives in CI 44797427059 passed | Private NAS acceptance remains WP-22 | Retain NAS gate |
| WP-06 / WP-07 | Hardened image / Compose | Preview web/tools slices verified | PR #8 | Actual amd64 build, Compose, non-root/read-only startup, mount/auth/mode/persistence/restore smoke passed in CI 44797427059 | Full worker Compose/operations integration remains | Full packages remain partial |
| WP-08 | Extended CI and container verification | Merged, software verified | PR #8; main CI 44798414658 success | Lock/audit, 170 tests, 2 browser tests, actual build/Compose/container/restore, image/secret scan and SBOM passed | Main is not branch-protected (API 404) | Enforce manual reviewed-green-PR gate |
| WP-10 | Versioned container release pipeline | Verified, published | `v0.1.0-preview.1`; PR #9 recovery fix | Original checks/build 44815669883; publication completion 44817372155; pulled digest, signed origin/SBOM and install assets verified (RELEASES.md) | None for preview publication; NAS deployment remains unperformed | Separately authorized synthetic WP-22 |
| WP-47a / WP-48 / WP-49 | Backup / install / rollback | Preview slices implemented; CI restore verified | PR #8 | Install/restore/update/debug guides; actual isolated container restore passed in CI 44797427059 | Full archive/NAS/two-version acceptance remains outstanding | Retain full package gates |
| WP-47a | Complete software-side consistent backup and isolated restore | Merged, software verified | PR #27, merge `4574d7b` | 558 Linux tests, nine browsers; final PR CI `45010127373` and main CI `45024467489` passed | Private NAS destination/retention/acceptance separate | Complete software scope |
| WP-23a | Preferred compatible archive editions | Merged, software verified | PR #28, merge `7025dfd` | 572 Linux tests, ten browsers; final PR CI `45028058218` and main CI `45028727303` passed | Private NAS acceptance separate | Complete software scope |
| WP-23b | Direct unchanged PDF and bounded ZIP download | Merged, software verified | PR #29, merge `7fdb40b` | 590 Linux tests, eleven browsers; final PR CI `45031690831` and main CI `45032500732` passed | Private NAS acceptance separate | Complete software scope |
| WP-29 | Durable project graph, revisions, CRUD and duplication | Merged, software verified | PR #30, merge `6927dff` | 601 Linux tests, twelve browsers; final PR CI `45035653508` and main CI `45036526836` passed | Private NAS acceptance separate | Complete software scope |
| WP-30 | Shared list, reserve slots and automatic numbering | Merged, software verified | PR #31, merge `25d4b04` | 616 Linux tests, thirteen browsers; final PR CI `45040247536` and main CI `45041169340` passed | Private NAS acceptance separate | Complete software scope |
| WP-31 | Participants, guests and saved project defaults | Merged, software verified | PR #32, merge `6d4cd99`; browser correction PR #33, merge `53aaced` | 630 Linux tests, fourteen browsers; final PR CI `45045456240`, correction CI `45047209870` and main CI `45048123486` passed | Private NAS acceptance separate | Approved six-WP sequence complete; stop |
| WP-34 | Explicit ensemble roles and playable mapping editor | Merged, software verified | PR #35, merge `b174773` | Local 565 passed/81 platform skips; 646 Linux tests, fifteen browsers; final PR CI `45058429483` and main CI `45059301957` passed | Private NAS acceptance separate | Complete software scope |
| WP-35 | Scoped replacement and concrete edition preference rules | Merged, software verified | PR #36, merge `7190045` | 661 Linux tests, sixteen browsers; final PR CI `45063691091` and main CI `45064524288` passed | Private NAS acceptance separate | Complete software scope |
| WP-32 | Central assignment and edition resolver | Merged, software verified | PR #37, merge `7b6e6fb` | 685 Linux tests, sixteen browsers; final PR CI `45069483361` and main CI `45070646957` passed | Private NAS acceptance separate | Complete software scope |
| WP-33a | Read-only matrix and effective provenance | Merged, software verified | PR #38, merge `52114f4` | Local 615 passed/81 skips; 696 Linux tests, seventeen browsers; final PR CI `45074373994` and main CI `45075310004` passed | Private NAS acceptance separate | Complete software scope |
| WP-33b | Exact direct matrix cell and saved-default edits | Merged, software verified | PR #39, merge `88ef45a` | 714 Linux tests, eighteen browsers; final PR CI `45085495233` and main CI `45086565420` passed | Private NAS acceptance separate | Complete software scope |
| WP-33c | Atomic matrix batch edits and retained reset | Software verified; integration pending | PR #40, source `04d2ff0` | Local 652 passed/81 skips before final refinements; 736 Linux tests, nineteen browsers; full CI `45090329532` passed | Private NAS acceptance separate | Final docs-head CI, merge/main then stop |

## Current-feature Synology test distribution — 2026-11-24

- Verified base `fd0ed9ce0b4efeb05c7210f237dcb7896c38a31a`, integrated PR #50;
  final PR CI `45347700944` and post-merge main CI `45350687436` passed. No open
  PRs or unfinished WP-38b/WP-39 work found. Existing deployment drafts preserved
  on dedicated `feature/synology-current-test` as checkpoint `fcc8547`.
- Implemented: worker-aware container entrypoint/maintenance ownership, isolated
  standalone Compose/tools, guarded host preparation, German runbook, original
  demo PDFs through normal manual review, corrected capability UI, full actual
  Compose/TLS-browser verification and immutable digest packaging/publication.
- Local Docker unavailable. Full Linux stack acceptance verified below; publication
  still pending, no test image/digest or NAS success claimed. Main is
  not branch-protected (API 404); manual reviewed-green-head gate remains required.
- Stop after this package. No OCR/enhancement/marchbook/printer development.
- Targeted local tests: 43 passed/one Windows symlink skip; Ruff/lock/system and
  migration drift passed. Full regression started; local browser attempt failed
  because Node.js is absent (22 failed before driver start/four POSIX skips), not
  a browser success. Linux CI must exercise the complete browser/container gate.
- Dedicated PR #51 opened. Full NAS-profile acceptance also covers ensemble UI,
  multi-page inspection, independent STATUS markers, exact-version/model pins,
  disabled direct routes and denied partial-batch downloads; not yet CI verified.
  Subsequent packaging/persistence/release/gateway affected suite: 26 passed.
- CI `45377092525` at `0dceb27`: Foundation passed all 953 Linux tests and 26
  browsers, dependency audit/system/migration checks. Container build, existing
  smoke/publication/restore and simple installation passed. New stack browser
  stopped at required indexing confirmation checkbox absent from the test;
  test corrected without weakening the mandatory user confirmation. Full stack,
  final-head CI, merge and publication remain pending.
- First local full regression ran during demo changes: 823 passed/129 platform
  skips/one stale collected one-page expectation failed against updated two-page
  demo. Current targeted demo passed; immutable-source full rerun in progress.
- Immutable-source local rerun passed: 824 tests/129 Windows platform skips in
  1325.56 s. CI `45380788140` passed Foundation again; the stack performed actual
  indexing and PDF rendering, then its strict label selector failed against the
  required-field label suffix. Match the established review browser selector;
  no business/UI/security behavior changed. Stack and publication remain pending.
- Real stack `45393521026` isolated HTTP-500 cause to SQLite reader-to-writer
  upgrade in nested canonical approval while the singleton worker writes.
  Add write-first conditional no-op CAS before nested approval, preserve exact
  revision and atomic enqueue; report bounded DB contention as actionable 409.
  Add query-order and independent file-backed SQLite writer regression. Temporary
  CI frame capture removed; actual stock NAS-profile stack remains mandatory.
- CI `45396565551`: Foundation passed with SQLite writer regression; stock
  full stack confirmed all six original synthetic PDFs through actual UI and
  worker publication. Participants/ensemble edits reached; matrix test expected
  a contiguous instrument/part label instead of its explicit notation fields.
  Select the exact visually reviewed file UUID; no assertion/authorization weakened.
- CI `45399921524` passed Foundation; real matrix exact override persisted through
  reload. Stack reached preflight, where the wrapped output label includes option
  text in its accessible name. Target the validated `variant` select explicitly.
  Full-stack PDF/recovery/security completion and publication still pending.
- **Verified software checkpoint:** CI `45403811456`, source head
  `68f0fcf74c81f599a22bf46e1f8dc80de670c882`, passed 956 Linux tests, 26 browsers,
  locked dependency audit, system/migration/format checks and complete hardened
  container/security acceptance. Actual standalone current Compose/TLS browser:
  interactive account/login/secure cookies/CSRF, all six original PDFs indexed,
  every page rendered and explicit human-action inspection/approval recorded,
  singleton worker publication, participants/ensemble/matrix override/reload,
  acknowledged missing notes, three personal reading/regular A4/A3 print PDFs,
  excerpt/contents, authorized downloads and anonymous denial, stale status and
  targeted regeneration. Actual crash-after-link recovery, cancellation/partial
  failure with denied download, immutable snapshot/exact version pins, independent
  STATUS, host+web+worker RAW write/rename/delete denial and restart persistence
  passed. Unrelated container/volume inventories unchanged. Trivy HIGH/CRITICAL
  vulnerability/secret gate passed; CycloneDX SBOM/image metadata retained in CI.
- Reviewed complete diff from verified base; no unresolved PR review, conflicts,
  private data or unrelated changes. Final documentation-head CI, merge/main CI,
  test-only artifact promotion/pull/stack and digest-pinned distribution remain.
  Physical Synology/DSM/TLS/ACL/resource/restore acceptance was not performed.
- PR #51 merged as `4ccd2698204a1e69ec7c1c4f128acf8e6c65d809`; final head CI
  `45407719536` and post-merge main CI `45411431365` passed. Reviewed merge tree
  matched; primary worktree clean/main before publishing `v0.1.0-test.1`.
- Release `45415635235`: all mandatory checks/candidate export passed; published
  exact tested bytes to `ghcr.io/tostman1/notenarchiv:0.1.0-test.1`, digest
  `sha256:f628501dbc3fbe65c4e53bb2ab6c4723bd4014bca582656383ffd528df543e5a`.
  Pulled digest and complete stack passed again, provenance/SBOM attestations
  completed. Only announcement packaging failed due to indented bash heredoc.
  Preserve image/tag; fix packaging and recover original hash-verified artifact,
  do not rebuild. Final source Compose now pins this actually verified digest.
  Packaging completion is not yet claimed.
- PR #52 packaging recovery uses `fix/synology-test-publication` from synchronized
  main, not unfinished business work. Targeted packaging/release/availability CI
  tests: 26 passed/one Windows bash skip. Independent anonymous GHCR manifests
  verified version tag equals published immutable digest. Local cryptographic
  source/SBOM attestations verified against exact original source/signer workflow.
  New Linux CI must also parse all multiline release shell blocks with bash -n.
- **Completed / verified test distribution, 2026-11-25:** PR #52 merged
  `01a00d9a585bd9c7c42e3cbf8f5934860309239c`, exact-head CI `45421346339` and
  main CI `45424991627` passed. Recovery `45434860531` succeeded using original
  candidate archive/hash, no rebuild/overwrite; published-digest full stack passed
  again and prerelease installation assets are available. Independently verified
  all seven asset hashes, six safe bundled files vs exact tag source, standalone
  Compose/guide/digest equality, final source Compose, 50-component SBOM and
  signed recovery origin with original source/artifact pin. Bundle hash and URLs
  recorded in docs/RELEASES.md. Image remains `0.1.0-test.1` / digest `f628501d…`.
- Resume after server restart preserved already-completed release and PR #53 CI
  governance work; no repeat publication, test rebuild or unrelated edits. Final
  work is documentation only. Primary worktree returns clean/synchronized main
  after its exact-head/documentation CI. Stop this package; physical DS224+ DSM,
  ACL/network/TLS, SQLite/WAL, resources/recovery and restore acceptance remains
  owner-side. No real data or NAS deployment performed.

## Owner-approved print PDF and export management — 2026-11-23
- WP-38b integrated PR #49 as `bacc597b7bad28eece48c34271b1b344c7555417`;
  final CI `45278315093` passed 926 Linux tests/25 browsers plus full hardened
  publication/restore/security checks. Main CI `45335478658` passed; clean synchronized
  primary main matched reviewed tree before WP-39. No duplicate integration.
- WP-39 in progress on `feature/wp-39-export-library`: unified bounded artifact/run
  library, per-person current-scope stale reasons vs historical exact input/output
  integrity, targeted preflight and variant binding, independent archive reading
  artifacts and secure ZIP. Initial six library cases and subsequent 42 export/
  snapshot/preflight/print regression passed. Real Linux one-person/archive crash/
  history tests and actual browser/container acceptance added; full gates pending.
- Targeted library/authorization/snapshot rerun passed 32 tests. Expanded 13 library
  tests passed; concurrent full-suite execution caused three existing parser-lock/
  availability failures in unrelated historical/preflight tests. No parser guards,
  timeouts or assertions changed. Serial final regression is required.
- Full local WP-39 regression passed: 812 tests/129 Windows platform skips in
  1105.51 s before final classification/ZIP/metadata guards; affected rerun passed
  48 tests. Added explicit damaged-batch-member gating and actual two-document
  project-free archive reading acceptance through real copy/review/publish services.
  Browser regression and mandatory Linux final-head/merge/main gates pending.
- Final affected suite passed 48 tests; classification denies a damaged batch's
  otherwise intact member without claiming source invalidity. Multi-document archive
  fixture requires the container matrix acceptance to use its explicitly pinned
  preferred assignment instead of assuming one physical edition; assertions retained.
- Final 16 export-library cases passed, including role changes and unchanged project
  archiving. Browser rerun passed all 22 local cases/four POSIX skips in 274.37 s;
  exact shell menu expectation includes the approved Notenausgaben link. Ruff/format/
  system/migration/lock/diff checks passed; complete final diff reviewed. Linux final-
  head CI and conditional PR/main gates remain. No extra work package started.
- First WP-39 PR CI `45344509420`: 946 Linux tests passed; library ZIP browser
  failed because scratch was derived from the shared local log root instead of
  canonical file-backed SQLite DATA. Anchor real ZIP scratch to DB parent (isolated
  in-memory unit profile retained). Container multi-edition fixture exposed missing
  deliberate preference before later excerpt acceptance; order fixture after the
  existing preference gate. No auth/root/hash/assertion weakened; corrected CI pending.

- WP-38a integrated PR #48 as `4659575c3a3c1841b721fc9990297071183e5e67`;
  final CI `45265622771` passed 888 Linux tests/24 browsers and full container/security.
  Post-merge main CI `45268896712` passed; exact reviewed tree matched, main clean.
- WP-38b in progress on `feature/wp-38b-print-pdf`: isolated renderer/Form XObjects,
  explicit composition origins, immutable separate print authorization/variant,
  project-free archive print pins, safe shared publication and local PDF.js preview.
  Targeted renderer/authorization/download/project suite: 45 passed. New real Linux
  publication/crash/cancel and browser/container print acceptance added; full gates pending.
- Final print authorization/renderer/download refinement rerun passed 33 tests;
  explicit transformed-media overflow negative passed. Both visual A4 halves match
  synthetic originals at exact physical pixel scale; transparency/active-content
  and original crop/rotation preservation covered. All 22 local browsers passed,
  three physical Windows skips. Full regression and Linux exact-head gates pending.
- Full WP-38b local regression passed: 798 tests/125 platform skips in 1024.27 s
  before final complete-source/hash/manifest guards, which passed 33 affected tests
  and explicit overflow rejection. All 22 local browsers passed/three POSIX skips.
  Ruff/format/system/migration/lock/diff checks passed. Full diff reviewed: no printer,
  no reading overwrite, no insecure preview or weakened file/DB guards. Minimal
  archive schema slice required by archive print output documented in PRINT_PDF.md.
  Real Linux final-head acceptance and merge/main gates remain; WP-39 not started.

- Reverified actual WP-37c integration: PR #47 merged at
  `06e8b3546d690d9395515fe9cce708ca8a8da27a`, final CI `45256041092` and
  main CI `45259372536` successful (859 Linux tests/24 browsers). No review threads;
  merged tree equals reviewed head; primary main clean and remote-synchronized.
- WP-38a started on `feature/wp-38a-print-layout`. Pure frozen occurrence/page/sheet
  planner, exact A4 consecutive music pairing, odd remainder, whole native A3/
  landscape/custom/crop geometry, rotation/UserUnit/origin transforms and manifests.
  Initial 28 targeted tests passed. Full regression and PR/CI/main gates pending.
- WP-38a full local regression passed: 774 tests/113 Windows platform skips in
  1010.45 s; final real-PDF inspection-to-plan addition passed with 29 targeted tests.
  Ruff/format/system/migration/lock/diff checks passed. Complete planner diff reviewed:
  pure immutable data, no I/O/auth/publication effects, exact boundary/geometry guards.
  No new UI requires local browser changes; full Linux/browser/container CI remains
  mandatory at the exact PR head. No renderer or next package started.

## Owner-approved personal PDF continuation — 2026-11-23

- WP-37b integrated via PR #46, final head `08b3c9de6ef9cb8bae41a43b552645892acffdba`:
  CI `45231098671` passed 832 Linux tests/23 browsers and all container/security checks.
  Merge `20d38494aaa65073b51a63a6ac1b39842e53de1e` passed main CI `45245754960`.
  Reviewed merged tree matched; clean primary main synchronized before WP-37c.
- WP-37c in progress on `feature/wp-37c-excerpts-contents`: current resolver-bound
  excerpts/single-part replacement, participant-free full contents authorization,
  immutable historical excerpt source/pin selection, shared publication/downloads
  and German project/matrix/history navigation implemented. Initial affected suite:
  42 passed. Added real Linux crash/restart/output-history tests and browser/container
  acceptance for all kinds. Full regression, final review and integration gates pending.
- WP-37c final affected snapshot/composition/selection/reopen suite passed: 42 tests;
  contents-only exact receipt/download and independent SQLite reopen exercised.
  Historical selection narrowed verification to requested eligible exact pins,
  avoiding unrelated corrupted historical files; both focused guards/selection
  tests passed. Browser regression passed 22 tests/two Windows physical skips
  in 336.67 s. Linux real publication/browser tests remain mandatory before merge.
- First full WP-37c run: 733 passed/110 Windows platform skips/four failures during
  concurrent parser verification and an invalid synthetic override setup. Corrected
  setup still tests fail-closed legacy metadata; final targeted selection/guard cases
  passed. Serial full rerun is required, without weakening parser limits or assertions.
- Serial full regression passed: 744 tests/110 Windows platform skips in 1080.66 s
  before last contents/no-active-people/strict source-selection additions, which passed
  targeted verification. All 22 local browsers passed/two physical skips. Ruff/format/
  system/migration/lock/diff checks passed; complete diff reviewed. Real Linux final-head
  CI/PR/main gates remain mandatory. No WP-38/39, OCR, printing, deploy or release.

- Verified clean main `6bf3c87f6a2261ed952ba51239f5f93ab847662c`, merged PR #45 and
  successful main CI `45201911838`. Preserved and fully reviewed local checkpoint
  `837b2013b8b2f218955bdbf19c8d53444baced5d`; safely resumed its existing branch.
  Normal main merge `fe1691d` retained both route additions after one URL conflict.
  No reset, force push, branch deletion or additional worktree.
- WP-37b in progress: snapshot-only composition, durable immutable publication/stage/
  artifact/completion records, bounded verified staging, fenced receipts, batch-only
  authenticated downloads, German UI and dead-owner/parent-bound parser cleanup.
- Targeted composition/snapshot/download/process regression: 40 passed, one platform
  skip; independent SQLite snapshot/replay and download rerun: ten passed. Full suite
  and final refinements require verification. Real Linux process/filesystem and
  browser-to-worker/download acceptance added. Windows has neither Docker nor WSL;
  no physical publication claimed locally. Final-head Linux CI/PR/main gates remain.
  WP-37c not started.
- Full Windows regression passed: 728 tests/99 platform skips in 925.41 s before
  final inventory/cleanup/security refinements; affected rerun passed 45 tests/two
  POSIX scratch skips. Ruff/format/lock/system/migration/diff checks passed.
- Browser regression: 21 passed/one physical Linux skip/one existing editions timeout.
  Unchanged isolated editions browser passed in 19.25 s; no assertions/timeouts
  weakened. Preflight/authorization browsers also passed targeted verification.
  Linux final-head CI must verify all browser and physical publication cases.
- First PR #46 CI `45229173541`: real hardened container generation/security passed;
  Linux Foundation failed 20 tests (812 passed). Isolated-root acceptance found
  generation scratch derived from local log root instead of canonical DB DATA,
  failing closed on overlapping roots. Corrected to DB parent; a synthetic parent-
  death test script also needed escaped newlines. No root checks/assertions weakened.

## Owner-approved developer workflow maintenance — 2026-11-23

- PDF sequence paused. All unfinished WP-37b files preserved in local-only WIP
  commit `837b2013b8b2f218955bdbf19c8d53444baced5d` on
  `feature/wp-37b-personal-folders`; no push or premature PR. Verified clean worktree,
  switched to synchronized main `269793cc032f671cfe7b27c5c44142530e4f2556`, created
  `chore/dev-workflow-ci-optimization` in the primary worktree only.
- Managed foreground launcher, local-only dedicated capability login, static finder/
  collection/favicon and safe endpoint categories implemented. Initial 27 local/manual
  auth tests and two live lifecycle/stale-state tests passed. No reproduced manual
  credential defect established. CI baseline 10:00, Foundation 7:00/Container 2:53;
  concurrency/cache/classification changes pending full verification and actual CI.
- Package remains in progress: lifecycle edge cases/cleanup review, full regression/
  browser tests, workflow validation, final PR/CI/merge gates required. No PDF work resumed.
- Full browser regression passed: 22 tests in 328.44 s. Final targeted lifecycle
  tests cover real startup/static assets, kill yes/no, Ctrl+C cleanup, stale state
  and port-conflict listener preservation (four passed). CI classification/local
  capability/manual-auth targeted checks passed. Full regression still pending;
  final launcher timeout/isolated test-root refinements recorded separately.
- First full maintenance regression: 709 passed/81 skips/one cancellation readiness
  timeout in existing 1.5 s process-tree test while suites ran concurrently. Isolated
  unchanged process suite passed (13/one skip), followed by combined launcher/CI/
  process tests (24/one skip). No timeouts/assertions changed. Serial full rerun
  pending; previous attempted foreground rerun exited without complete result.
- Serial final full regression passed: 716 tests/81 platform skips in 828.29 s;
  no process cleanup assertion or timeout weakened. All 22 browsers passed.
  Ruff/format/system/migration/lock/diff checks and actual actionlint validation
  passed. Final review preserves existing required check names; main protection
  lookup confirmed HTTP 404/unprotected. Maintenance PR/actual after timings pending.
- PR #45 implementation head `d9f7eed6078c44791877e7fd8738c5a87d208783` passed
  complete CI `45197208105`. Foundation 10:41, Container 2:57 in parallel; total
  10:44 versus baseline 10:00. No demonstrated net wall-time improvement in this
  cold-cache sample; slower unit/browser execution dominated. Details recorded in
  DEV_WORKFLOW.md. No reviews/inline findings; final documentation-head CI pending.

## Owner-approved matrix and generation sequence — 2026-11-23

- WP-37a merged PR #44 as `269793cc032f671cfe7b27c5c44142530e4f2556`; final-head
  CI `45177706547` and main CI `45179603788` passed; exact reviewed tree matched,
  primary main clean/synchronized. WP-37b started on `feature/wp-37b-personal-folders`.
- WP-37b initial implementation adds artifact model/migration, generated-byte staging,
  worker composer/publication/reconcile hooks and complete-run-only download routes.
  Two pure personal/placeholder composition integration cases passed. Not complete
  or merge-ready: POSIX publication/recovery/failure/cancellation tests, immutable
  artifact guards, bounded memory/output manifests, safe stage retry cleanup,
  human-readable naming, browser/UI wiring and full regression remain. Existing
  unavailable-renderer tests/UI assertions must be updated to the real handler
  contract without weakening safety. No generation button enabled yet. Source
  checkpoint remains uncommitted; no successful physical publication claimed.

- WP-37a PR #44 head `a69cb41ce76f8e865c50049fb5ff07f3c0522371` passed full
  CI `45175409416`: Linux unit/browser, runtime audit, migration/system checks,
  actual hardened amd64 image with locked ReportLab/native dependencies, synthetic
  container/restore/publication/install and vulnerability/secret checks. Exact PR
  head and full diff reviewed; no reviews/inline findings, merge state CLEAN.
  Final documentation-head CI and merge/main gates remain.

- WP-36b merged PR #43 as `b4c16f9cc505185be78599c0cd9c271222c3e298`; final-head
  CI `45168812914` and post-merge main CI `45170929102` passed. Reviewed merged
  tree matched exactly; primary main clean/synchronized, no blocking findings.
- WP-37a started on `feature/wp-37a-pdf-composition` from verified main. Isolated
  shared reading-PDF builder, German contents/reserves, optional personal cover,
  missing placeholders and Unicode font authoring added; original page geometry/
  vector streams copied without overlays or pairing. ReportLab 5.1.0 and transitive
  dependencies locked; actual metadata/font license notices inspected. Initial
  eight composition tests passed; expanded limits/text/format tests pending.
- WP-37a expanded composition/existing PDF foundation suite passed: 57 tests,
  one Windows/POSIX permission skip in 96.09 s. Ruff/format/lock/system/migration/
  diff checks passed. Full regression and all existing browsers running; no PR,
  integration or output-generation success claimed. Contract in PDF_COMPOSITION.md.
- WP-37a existing browser regression passed: 22 tests in 267.70 s. Full local
  regression remains pending; no new UI route is introduced by the pure builder.
- Final builder review adds an explicit oversized-heading bound (no clipping),
  annotation fail-closed coverage and deterministic same-input composition test.
  All thirteen composition cases passed in 21.12 s after these refinements;
  full-suite result is recorded separately when available.
- Full WP-37a local regression passed: 700 tests/81 platform skips in 739.94 s
  before final heading/annotation/determinism refinements, which passed thirteen
  targeted cases. All 22 browsers passed. Complete diff reviewed; source geometry/
  content untouched, bounded isolated parsing retained. Linux PR CI pending.

- WP-36b PR #43 implementation head `32a180b241e6cc9da0d8abf9ddf2ef3771986f47`
  passed full CI `45166737828`: Linux tests/browser, runtime audit, migration drift,
  hardened amd64 image, container/isolated restore/synthetic archive publication,
  install smoke and image vulnerability/secret checks. Final head/base/diff reviewed;
  no submitted reviews or inline comments, merge state CLEAN. Documentation acceptance
  update needs final-head CI before merge and post-merge main verification.

- WP-36a merged through PR #42 as `ed22fbcdfe4e2d7e5c94f8fb9674b2a9d74f9c28`;
  final-head CI `45150655373` and post-merge main CI `45152636899` passed. Clean
  primary main matched origin and reviewed merged tree. No unresolved findings.
- WP-36b in progress on `feature/wp-36b-generation-snapshots` from that verified
  main: canonical dependency capture, immutable snapshot/run/pin models, atomic
  preflight-bound enqueue, protected withdrawal and SQLite update guards added.
  Worker loads pinned input only and fails closed while PDF renderer is unavailable.
  No UI generation button or successful PDF output is presented. Twelve targeted
  snapshot/persistence cases were run: eleven passed, one POST UUID normalization
  failure fixed; final rerun pending. Existing thirteen preflight cases passed.
  Package remains incomplete: concurrency/recovery/browser coverage, guard review,
  documentation/traceability, full regression and PR/CI/merge gates still required.
- Continuation closes replay and relational-selection gaps: signed request UUID,
  idempotent authorization, participant/position pins including reserves/missing,
  conservative canonical publication/catalog dependencies and SQLite trigger refresh.
  Thirteen snapshot tests passed; independent reopen/concurrent replay plus new
  authorization browser passed (three tests). Generic cancellation/unavailable-renderer
  execution tested: no false success. Full regression and browser gates pending.
  Snapshot contract/limitations recorded in GENERATION_SNAPSHOTS.md. No PDF composition.
- Final security review added generic-queue duplicate-job denial and run/job identity
  validation, bounded snapshot payload and missing-library-change atomic recheck.
  Fifteen snapshot tests passed after these refinements; full suites launched before
  those refinements are still pending and targeted results are recorded separately.
- Full WP-36b browser suite passed: 22 tests in 304.49 s. Full local regression
  remains pending. Final authorization refinements require only affected targeted
  verification; no browser assertions or existing regression tests weakened.
- Final snapshot/queue/SQLite regression passed: 47 tests in 130.85 s after generic
  enqueue protection and formatting corrections. Full local regression pending;
  no PR or integration completion is claimed.
- Full local WP-36b regression passed: 688 tests/81 Windows platform skips in
  768.50 s before final queue/validation refinements, which passed the 47-test
  affected regression. All 22 browsers passed; Ruff/format/system/migration/locked
  dependency/diff checks passed. Complete diff reviewed for exact pins, transaction
  scope, replay, auth/CSRF, unchanged source files and no false output success.
  Software implemented locally; Linux final-head CI and merge/main gates pending.

- WP-36a implementation head `a519af64cdc0cb70652b540b146803adadcdccf6` in
  PR #42 passed full CI `45148831865`: Linux unit/browser checks, locked runtime
  audit, system/migration drift, hardened amd64 image, synthetic publication/restore
  and image vulnerability/secret checks successful. Final head/base and complete
  diff reviewed; no submitted reviews or inline comments, merge state CLEAN.
  Documentation acceptance update requires final-head CI; merge/main still pending.

- WP-33d integrated through PR #41, final head `daff51d2902bcc3eefcf32473422b26d45197770`
  passed full CI `45142636153`; merge `cac372c5fff4344ca3263df8e6227038bce28a62`
  passed post-merge main CI `45144408952`. Merged tree exactly matched reviewed head;
  clean primary main matched origin. No reviews/inline comments or blocking findings.
- WP-36a started from that verified main on `feature/wp-36a-preflight`. Selected
  participant/position report reuses central verified resolver; missing decisions,
  blocking ambiguity/invalid/corrupt/unreadable inputs, unreviewed candidate notices,
  part/edition provenance and isolated bounded structural/layout inspection added.
  Signed actor/report-bound acknowledgements are inspection-only, no generation
  job or immutable durable authorization implied (WP-36b). Thirteen integration tests
  and the missing/conflicting/corrupted-input browser passed; full gates pending.
  Final additions verify matching-hash malformed PDFs through the actual isolated
  parser, withdrawn exact editions, foreign actors and duplicate acknowledgement
  keys; no assertions weakened. Full regression/browser suites running. Ruff/format,
  locked dependency, system/migration checks passed after formatting the route file.
- WP-36a full browser suite passed: 21 tests in 322.06 s. Full local regression
  passed: 670 tests/81 Windows platform skips in 683.36 s before final refinements;
  final thirteen preflight integration tests passed in 27.83 s, including the
  duplicate-selection guard. Complete diff reviewed; auth/CSRF, safe read-only
  inputs and exact resolver selection remain unchanged. Linux PR CI pending.

- WP-33d PR #41 source head `9373806dc9ceba80767e9e3dbd02e6cd3f7f21b0`
  passed complete CI `45141008382`: Foundation and hardened amd64 container/security/
  synthetic publication/isolated restore checks successful. PR head/base confirmed,
  full diff reviewed, no submitted reviews or inline comments; merge state CLEAN.
  Existing pinned actions emit a non-blocking Node 20 deprecation annotation while
  running on Node 24; no infrastructure change included. This documentation update
  requires its own final-head CI before conditional merge and post-merge main gate.

- Approved order: WP-33d → WP-36a → WP-36b → WP-37a → WP-37b → WP-37c, separate
  primary-worktree branches/PRs, final-head and post-merge main CI gates. No releases,
  deployment, private data, branch deletion or additional packages authorized.
- Initial clean WP-33c branch safely fetched and main fast-forwarded to
  `2ff6e01225eba6c5baf74b1c14baf70cb87ad803`; latest full main CI `45131526501`
  verified successful by GitHub CLI. No open PR; locked offline dependency sync passed.
  Historical HANDOFF.md is superseded by explicit owner continuation, not a takeover.
- WP-33d in progress on `feature/wp-33d-matrix-performance`: bounded filters,
  paged HTMX/no-JS navigation, shared header choices and retained integrity/revision
  checks. Three new integration/performance tests and new 100 × 50 browser passed;
  existing three matrix browsers passed. Ruff/format/lock/system/migration/diff checks
  passed. All twenty browsers passed (300.90 s); final URL/reload refinement and
  four filter/performance integration cases subsequently passed together with the
  large browser (five tests). Full local regression passed: 658 tests/81 Windows
  platform skips in 740.29 s before final URL/catalog/test refinements, which passed
  targeted reruns. No PR/merge/CI success claimed yet.
- Single Windows synthetic sample: small 3 × 3 response 105 SQL/0.759 s/45,824 bytes;
  100 × 50 project, 25 × 10 window 105 SQL/3.306 s/1,194,732 bytes. Same two tiny PDFs
  repeated; per-file verification costs remain. NAS/heterogeneous/archive load
  acceptance separate. Details and window-local deviation limitation in MATRIX.md.
- Final targeted sample: 105 SQL in both cases, 0.360 s small/2.422 s large;
  45,850/1,194,290 HTML bytes. GitHub API became intermittently unavailable after
  initial successful verification; current protection/PR/CI gates cannot be claimed.
- GitHub connectivity recovered for main-CI verification and protection lookup:
  main remains unprotected (HTTP 404); reviewed green-PR gate must be manual.
  Final catalog bound (2,000 header choices) and five performance/filter cases passed.
  Existing matrix/persistence rerun: twelve passed. Full diff reviewed; no resolver,
  security, edition eligibility or revision fences weakened. Linux/CI gates pending.

## Owner-approved assignment and matrix sequence — 2026-11-22

- Authorized WPs: WP-34 → WP-35 → WP-32 → WP-33a → WP-33b → WP-33c, each in
  the primary worktree with a separate feature branch/PR and final-head/main CI.
  No linked worktrees, NAS/private data, force-push, branch deletion, deploy/release.
- Initial repository verification: clean main/origin main both
  `7f07243f6ab30ee8235c8b584a583b82c706f205`, full CI `45049924473` success;
  previous six WPs integrated, no open PR. Historical HANDOFF.md is superseded
  by actual Git/progress and this new explicit owner continuation, not a takeover.
- WP-34 in progress on `feature/wp-34-ensemble-mapping`: reuse protected project
  graph and revision services; German role/mapping CRUD and participant role editor,
  exact-variant mapping component and append-only change evidence. Fifteen targeted
  model/persistence tests and all fifteen browsers passed. First full local Windows
  regression: 556 passed/81 POSIX skips/two pre-existing queue timing failures;
  independent cases passed but the isolated full rerun still failed an immediate
  claim (561 passed/81 skips/one failure). Synthetic clock probe found Python
  microseconds ahead of SQLite's millisecond statement clock. Immediate enqueue
  now uses that same DB timebase as claim; 43 queue/lifecycle tests passed,
  including forced future Python-default regression. No lease/fencing/retry
   conditions or assertions weakened. Final local full regression passed: 565 tests,
   81 platform skips; all fifteen browsers passed again after the cause fixes.
- Initial PR #35 CI `45055233428` passed all Linux unit tests and the new ensemble
  browser, but failed an existing piece-list browser's immediate reload after POST.
  The correction waits for the actual redirected response, incremented revision
   and load before reload; both piece/ensemble browsers passed. Source `424defd`
   passed full CI `45057377256`: 646 Linux tests, fifteen browsers, system/migration
   drift, runtime audit, actual hardened amd64 image/Compose/ensemble role+mapping,
   archive/download/backup/isolated restore, both install variants and image
   vulnerability/secret checks. Full diff/commits reviewed, no submitted reviews or
   unresolved threads. Final head `97b7ba4` passed CI `45058429483`, merged as
   `b174773164acb0d6b6fab043529f25b0bec4b055`; main CI `45059301957` passed.
   Exact merged tree matched; primary worktree returned to clean main.
   No NAS/private data, deployment, release, force-push or linked worktrees.
- WP-35 in progress on `feature/wp-35-replacement-edition-rules` from that verified
  main. Reuse project/position preferences and replacements; global replacement
  revision/overlay-cycle checks, protected rule history, deliberate clear and
  German controlled editors. Full local regression: 578 passed/81 Windows platform
  skips before final history/invalid-rule/UI-status refinements; final targeted
  rule/persistence suite 15 passed and rule browser passed. All sixteen browsers
  passed. Ruff/format/lock/system/migration/diff checks passed, full diff reviewed.
  Source `22edbd9` passed complete CI `45062571782`: 661 Linux tests, sixteen
  browsers, system/migration drift, locked runtime audit, hardened amd64 image/
  Compose, actual project/global rule operations, archive/unchanged downloads/
  backup/isolated restore, both install flows and vulnerability/secret checks.
  Full commits/diff reviewed, no submitted reviews or unresolved threads. Final
  head `ce89e62` passed CI `45063691091`, merged as
  `71900452c3c8990c5d6816c203fd926dfde4f88e`; main CI `45064524288` passed.
  Exact merged tree matched; returned to clean primary main. No NAS/
  private data, deployment, release, force-push or linked worktrees.
- WP-32 in progress on `feature/wp-32-central-resolver` from that verified main.
  One read-only resolver snapshots project/default/role/override/rules and reuses
  shared pure edition choice; exact immutable results/provenance, missing/invalid/
  ambiguous/one-hop substitution, integrity checks and reserve bypass implemented.
  Local full regression 600 passed/81 platform skips before final four coverage
  additions; final resolver/persistence suite 24 passed. All sixteen browsers
  passed. Ruff/format/lock/system/migration/diff checks passed; complete diff
   reviewed. Source `f20655e` passed full CI `45068374035`: 685 Linux tests,
   sixteen browsers, system/migration drift, runtime audit, hardened amd64 image/
   Compose, actual resolver on isolated restored confirmed inputs, archive/download/
   backup/restore, both install flows and image vulnerability/secret checks.
   Initial container assertion used an arbitrary part instead of the preferred
   combined-PDF assignment; fixture now pins that exact assignment, original
   usability/provenance assertion retained. Full diff/commits reviewed; no submitted
   reviews or unresolved threads. Final head `0c076b8` passed CI `45069483361`,
   merged as `7b6e6fb2fc81c99e830677b2a5242a32ab3b748c`; main CI `45070646957`
   passed. Exact merged tree matched; no NAS/private data, linked worktrees/release/deploy.
- WP-33a in progress on `feature/wp-33a-matrix-provenance`, from verified clean main.
  German bounded shared-position × selected-participant matrix consumes only central
  verified resolver output. Desired/effective parts, edition UUID/provenance, missing/
  ambiguous/substituted/invalid states and non-editable reserves shown. Targeted
  eleven matrix tests and all seventeen browsers passed; final hash-label update
  also passed matrix browser. Initial full regression had 612 passes/81 platform
  skips/one missing test import, corrected with assertions unchanged. Full corrected
  corrected rerun passed: 615 tests/81 platform skips. Ruff/format/lock/system/
  migration/diff checks passed. Full CI `45073173161` on `800dd5a` passed:
  696 Linux tests, seventeen browsers, hardened amd64 image/Compose, actual matrix
  adapter over restored confirmed inputs, archive/download/backup/restore, both
  installation flows and vulnerability/secret checks. Full diff/commits reviewed;
  no submitted reviews or unresolved threads. Final head `560bcf8` passed CI
  `45074373994`, merged as `52114f4e20f012a76fdcdaeda02c0f1368889b7e`;
  main CI `45075310004` passed. Exact merged tree matched, primary main clean.
  No NAS/private data, deployment/release or linked worktrees.
- WP-33b in progress on `feature/wp-33b-direct-matrix-edits` from verified main.
  Signed exact edition cell edits, protected old/new MatrixChange, existing saved
  default editor in headers, local hash-verified HTMX/no-JS forms, optimistic
  project/archive fences; no personal-list mutation. Targeted tests/browser passed;
  local full regression 631 passed/81 platform skips before final budget/archive
  coverage, which passed in targeted rerun (18 edit/persistence/asset tests).
  All eighteen browsers passed; final safety refinements passed both matrix browsers.
  Ruff/format/lock/system/migration/diff checks passed; full implementation diff
  reviewed. Initial CI `45083049948` failed an existing CRUD browser reload-before-
  redirect race; explicit POST navigation synchronization retains assertions.
  Matrix stale-tab test now reads its own timestamped choice token, preserving the
  old project revision. Both affected browsers passed locally. Source `2b6eec1`
  passed full CI `45084352726`: 714 Linux tests, eighteen browsers, system/migration
  drift, locked runtime audit, hardened amd64 image/Compose, actual exact matrix
  edit on confirmed synthetic inputs, archive/download/backup/isolated restore,
  both install flows and vulnerability/secret checks. Full diff/commits reviewed;
  no submitted reviews or unresolved threads. Final head `21064be` passed CI
  `45085495233`, merged as `88ef45a4f9f5b7e6e0a381dcc41eeb18410b5190`;
  main CI `45086565420` passed. Exact merged tree matched; primary main clean.
  Branch protection unavailable; explicit checks performed. No NAS/private data,
  deployment/release or linked worktrees.
- WP-33c in progress on `feature/wp-33c-atomic-matrix-batch` from verified main.
  Same-person bounded exact multi-cell edits and non-destructive selected reset;
  active flag retains historical override identities/pins, central resolver ignores
  reset overrides. Full validation, one project revision transaction and protected
  per-cell history; no shared-list/numbering changes. Twenty-one batch/persistence
  tests and all nineteen browsers passed, including JavaScript-disabled selected
  reset. Actual SQLite concurrent
  batches yield one save/one conflict and independent reopen preserves reset/pins.
  Full local regression 652 passed/81 platform skips before final budget/inactive-
  arrangement coverage; final matrix/batch/persistence suite 49 passed and all three
  matrix browsers passed. Ruff/format/lock/system/migration/diff checks passed;
  full diff reviewed. Source `04d2ff0` passed full CI `45090329532`: 736 Linux
  tests, nineteen browsers, system/migration drift, locked runtime audit, hardened
  amd64 image/Compose, actual synthetic exact batch and retained reset in the
  isolated restored archive, worker publication/download/backup/restore, both install
  flows and vulnerability/secret checks. No submitted reviews or unresolved threads.
  Final documentation-head CI and merge/main gates remain; no further WPs started.
- Authorized sequence functionality now covers scoped roles/mappings, replacement
  and edition preferences, one central resolver, provenance matrix, direct exact
  edits/saved defaults and atomic batch/reset. Private NAS acceptance is separate.
  Matrix currently pages 25 positions by 10 participants; batches are bounded to
  25 cells, require deliberate per-position exact editions and abort on conflicts.
  Preflight acknowledgements, immutable generation snapshots and export/printing
  are not implied. Dependency-ready next packages after WP-33c integration:
  WP-33d (matrix filters/performance) and WP-36a (preflight/missing report).
  Recommendation: WP-33d first to validate 100-by-50 usability/query bounds, then
  WP-36a. Both require new authorization; stop after verified WP-33c main CI.

## Owner-approved archive safety and projects sequence — 2026-11-22

- Approved sequential WPs: WP-47a, WP-23a, WP-23b, WP-29, WP-30, WP-31, each
  from verified main with separate reviewed PR, final-head CI, conditional merge
  and post-merge main CI. No NAS data, deployment, release or branch deletion.
- Base: clean primary main `80193b413a5b1e1ad47f71c66d665de96e2e8c43`, full CI
  `44969319332` succeeded. No open PR at start. Historical HANDOFF.md is not
  current continuation authority; latest explicit owner sequence controls.
- WP-47a software verified on `feature/wp-47a-consistent-backup`: exclusive service
  locks/SQLite write barrier, actual file/config/secret capture, independent RAW
  read-only verification, trusted manifest and isolated restore. Source `66926f9`
  passed complete CI `45009366615`: 558 Linux tests, nine browsers, migration
  drift, runtime audit, hardened amd64 image/Compose, actual copied multi-part
  archive backup/restore/reopen, published/candidate first installs and image
  vulnerability/secret scans. Local baseline: 477 passed/75 platform skips and
  nine browsers; final CLI regression: three passed/25 physical Linux skips.
- Full diff/commits reviewed; no submitted reviews or unresolved threads at this
  source checkpoint. Earlier failures were synthetic immutable-file/lease setup
  and CLI environment access; corrected without weakening protections/assertions.
  Final PR head `2f384575f850e95c9e7612bad83cbd9e2208c8b9` passed CI
  `45010127373`, merged as `4574d7bdcae80aac06bc5be898776013dc72036b`;
  main CI `45024467489` passed. Exact merged tree matched reviewed PR head.
  No private NAS acceptance, real data, release or deployment claimed.
- WP-23a started on `feature/wp-23a-preferred-editions` from that verified clean
  primary main. Protected preference/change models, exact-part edition component,
  German preference/reset/version-check UI and migration implemented. Targeted
  acceptance: 24 edition/library/persistence tests passed; full local regression
  491 passed/79 Windows platform skips before final two coverage additions (both
  passed in targeted rerun). Ten browsers passed; final UI-label/library refinements
  additionally passed two relevant browsers. Ruff, lockfile, system/migration
  drift and diff whitespace passed. Full CI `45027269366` on source `9c0ecd2`
  passed: 572 Linux tests, ten browsers, actual hardened amd64 image/Compose,
  independent worker publication/preferences, physical backup/restore/reopened
  preference history, both first-install flows and vulnerability/secret checks.
  Complete diff/commits reviewed; no submitted reviews or unresolved threads.
  Initial container-test setup lacked explicit Django settings; corrected without
  relaxing production settings or assertions. Final head `4a00320` passed CI
  `45028058218`, merged as `7025dfdd2a8fd242ce52edcee6fffffc974cf7ff`; main
  CI `45028727303` passed. Exact merged tree matched. No NAS/release/deployment.
- WP-23b in progress on `feature/wp-23b-direct-downloads` from that verified clean
  main: confirmed direct unchanged PDF/ZIP, bounded private streaming stages,
  signed explicit selection, combined-document deduplication, derivative preview.
  Local full regression: 507 passed/80 Windows platform skips before final
  timeout/scratch/failure coverage; final focused downloads 16 passed/two POSIX
  skips. Eleven browsers passed; final download safety refinements additionally
  passed its browser. Ruff/format/lock/system/migration/diff checks passed. Full
  implementation diff reviewed. Source `bcc2e5b` passed full CI `45030782487`:
  590 Linux tests, eleven browsers, system/migration drift, runtime audit, hardened
  amd64 image/Compose, actual unchanged PDF/ZIP staging, archive/preference and
  isolated restore/reopen, both installation flows and vulnerability/secret scan.
  No submitted reviews or unresolved threads at this checkpoint. Final documentation
  head `a1d03d4` passed CI `45031690831`, merged as
  `7fdb40b38c8c2d0e4b4a89716bfbe390e44f0cdc`; main CI `45032500732`
  passed. Exact merged tree matched. No private
  NAS data/destination, release, deployment or branch deletion.
- WP-29 in progress on `feature/wp-29-project-model-crud`, from that verified
  clean primary main. Durable project graph/revisions, isolated full duplication,
  German CRUD/archive/reactivate and migrations implemented. Targeted concurrency,
  persistence/model/UI: eleven tests passed. Full local regression 518 passed/81
  Windows platform skips before final pagination/clone refinements (targeted rerun
  passed); twelve browsers passed. Ruff/format/lock/system/migration checks passed
  after correcting synthetic script line length and line endings. Full diff
  reviewed. Source `8aad238` passed full CI `45034660243`: 601 Linux tests,
  twelve browsers, system/migration drift, locked runtime audit, hardened amd64
  image/Compose, actual project CRUD/clone on restored isolated DB, archive and
  download/backup/restore flow, both install variants and vulnerability/secret
  scan. No submitted reviews or unresolved threads. Final documentation-head CI,
  head `3e6f011` passed CI `45035653508`, merged as
  `6927dffbdfa221d9393162522d2215220531e727`; main CI `45036526836` passed.
  Exact merged tree matched. No NAS/release/deploy.
- WP-30 in progress on `feature/wp-30-shared-piece-list`, from that verified clean
  primary main. Shared list/derived numbering/reserves/repeats, atomic validated
  edits, acknowledged stable-ID replacement and protected history, German live
  library/drag-drop preview implemented. Targeted tests/browser passed; full gates pending.
  Local full regression: 533 passed/81 Windows platform skips before final personal
  parameter/empty-list coverage; final focused list/persistence 15 passed. Thirteen
  browsers passed; final contents-label update additionally passed list browser.
  Ruff/format/lock/system/migration/diff checks passed. Full source diff reviewed;
   Source `5e6299d` passed full CI `45039372553`: 616 Linux tests, thirteen
   browsers, system/migration drift, runtime audit, hardened amd64 image/Compose,
   shared-list insert/move/reserve clone, archive/download/backup/isolated restore,
   both install flows and image vulnerability/secret scans. Full commits/diff
   reviewed; no submitted reviews or unresolved threads. Initial browser search
   timeout fixed by synchronizing actual enhancement readiness, not weakening the
    live search assertion. Final head `43a2069` passed CI `45040247536`, merged
    as `25d4b042453d7539a27a2366447285824f5b2e71`; main CI `45041169340` passed.
    Exact merged tree matched; no NAS/private data/release/deployment/branch deletion.
- WP-31 in progress on `feature/wp-31-participants-defaults` from that verified
  clean primary main. Bounded subset/all/none, project guests, saved defaults,
  explicit master revision/name refresh, manual defaults and retained history.
  Local full regression: 544 passed/81 Windows platform skips before final scope/
  pagination coverage, which passed in targeted rerun (14 participant/persistence
  tests). Fourteen browsers passed; final origin/prefetch labels additionally passed
  participant browser. Ruff/format/lock/system/migration/diff checks passed; complete
   source diff reviewed. Full CI `45043669400` on `da915e6` passed: 630 Linux
   tests, fourteen browsers, system/migration drift, runtime audit, actual hardened
   amd64 image/Compose, saved participant/guest container operations, shared lists,
   archive/download/backup/isolated restore, both first-install flows and image
   vulnerability/secret scans. No submitted reviews or unresolved threads. Final
    PR head `9b98b695db8d831abdbb00c091f3eab7565a98f4` passed full CI
    `45045456240`, merged via PR #32 as `6d4cd99f801174b8b5e5599878180a367e29b79a`.
    Exact merged tree matched. Main CI `45046268589` passed 630 Linux tests but
    failed the participant browser's immediate reload during a guest POST redirect.
     Separate correction PR #33 on `fix/wp31-browser-checkpoint` changed only
     browser navigation synchronization and the sequence record. Its final head
     `75e017e581e29d60bf8979206d0861401e9628d8` passed full CI `45047209870`,
     merged as `53aaced4559d3aefc7a222bcf297881b9f043279`; post-merge main CI
     `45048123486` passed (630 Linux tests, fourteen browsers, complete container/
     security checks). Both merged trees matched reviewed heads, no unresolved
     reviews/threads; primary main was clean. No next WP started. No NAS/private
     data/release/deployment/branch deletion.

### Consolidated sequence completion

All six requested implementations are merged through separate PRs #27–#32.
WP-47a, WP-23a, WP-23b, WP-29 and WP-30 each have successful final PR and
post-merge main CI recorded above. WP-31 and its bounded browser correction passed
final PR and post-merge main CI. **All six packages are software-verified and
integrated. Stop after the documentation-only final record; no further development.**

Delivered software: complete consistent backup/isolated restore; protected exact
archive preferences; unchanged direct PDF/bounded ZIP; durable project graph and
revision/clone isolation; one shared numbered list with explicit reserves; selected
members/project guests and saved defaults with explicit master refresh. Original
PDF bytes, historical references, explicit selections, local-only data handling,
auth/CSRF/Django DEBUG=False and RAW read-only protections remain.

Private NAS backup destination/retention/ACL/filesystem/recovery acceptance remains
unperformed. No real association files/members were used. Published preview image,
tag and installation assets are unchanged; new source is not deployed or released.
Main branch protection is unavailable (API 404); reviewed green-PR gating is manual.
Earlier local Windows skips/queue timing and corrected browser/fixture setup issues
are documented separately from actual Linux and container acceptance.

Recommended next dependency-ready sequence (not started or authorized here):
WP-34 role/playable-variant mapping → WP-35 replacement and project/position edition
rules → WP-32 single assignment/edition resolver → WP-33a shared matrix/provenance.
WP-34 and WP-35 prerequisites are now implemented; WP-32 requires both, and WP-33a
requires WP-30 plus WP-32. Matrix editing/batch overrides and immutable generation
snapshots follow afterward under a new owner-approved sequence.

## WP-01 — Repository, development tooling and minimal CI

**Delivered** (branch `feature/wp-01-project-foundation`, from `main` at the
v2.0 spec baseline):

- `pyproject.toml` — Python `>=3.12,<3.13`; runtime dep `Django==5.2.10`;
  dev group `pytest==8.4.1`, `ruff==0.14.5`; Ruff target py312, line length
  120; pytest `testpaths = ["tests"]`.
- `uv.lock` — resolved with uv 0.12.5 against CPython 3.12.13 (12 packages).
- `tests/test_foundation.py` + `tests/smoke_settings.py` — interpreter
  baseline, Django 5.2 pin, isolated `django.setup()` smoke (DEBUG=False
  invariant), and the OP-04 `DEBUG_MODE` parse contract.
- `tests/conftest.py` — synthetic-fixture policy fixture (GR-14).
- `.gitignore`, `.dockerignore` — caches, venv, secrets, `.env`, local DB /
  logs / scratch / thumbnails, local `opencode.json`.
- `.github/workflows/ci.yml` — push to `main` + pull_request;
  `permissions: contents: read`; actions pinned to commit SHAs
  (`actions/checkout@v4` = `11d5960a...`, `astral-sh/setup-uv@v5` =
  `d4b2f3b6...`); steps: `uv lock --check`, `uv sync --locked`,
  `uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest`.
- `docs/LICENSES.md` — dependency license inventory mechanism; direct
  licenses verified from installed package metadata (Django BSD-3-Clause,
  pytest MIT, ruff MIT). No project LICENSE file created (owner decision
  pending, D-10).

**Actual local results** (Windows dev machine, uv 0.12.5, CPython 3.12.13):

| Check | Result |
| --- | --- |
| `uv lock` | ok, 12 packages resolved |
| `uv lock --check` | pass |
| `uv sync --locked` | pass, 11 packages installed |
| `uv run ruff check .` | pass (0 findings) |
| `uv run ruff format --check .` | pass (3 files) |
| `uv run pytest` | 8 passed |
| CI workflow YAML | parsed OK (local check; GitHub run not yet observed) |

**GitHub status:** branch pushed (`bf0b826` + `e8e7a95`), pull request #1
opened (`gh` CLI token on the dev machine is invalid; PR created via the
GitHub API with the stored Git credential). GitHub Actions CI on the PR
**passed**: run `44694745130`, job "Foundation (ruff + pytest)" success.
PR #1 merged into `main` (merge commit `bcdf272`) after CI success,
owner-approved.

**Notes:**

- No application code, app packages, or speculative features were created.
- `opencode.json` (local agent config) is git-ignored, not committed.
- Spec docs v2.0 were committed as `docs: commit specification revision 2.0
  baseline` on `feature/project-setup` and fast-forward merged to `main`
  before this work package started (owner-approved).

## WP-02 — Django skeleton and configuration

**Delivered** (branch `feature/wp-02-django-skeleton`, from `main`):

- `manage.py`, `config/` package: `settings.py` (DEBUG always False,
  security defaults, static/WhiteNoise, i18n de, domain roots, processing
  limits, logging baseline), `urls.py` (public `/healthz`), `wsgi.py`,
  `db.py` (SQLite foreign-keys + busy-timeout pragmas via
  `connection_created`), `env.py` (single source for environment parsing;
  full ARCHITECTURE.md §9.1 contract, typed and validated).
- Profiles: `nas` = deployment default (explicit env contract, secret from
  protected file, no auto-creation); `local` = explicitly selected dev
  profile (loopback-only bind enforced, synthetic roots under `.dev/`,
  dev secret generated 0600, roots auto-created). No production security
  setting is weakened by the local profile.
- App boundaries `apps/{accounts,catalog,members,archive,projects,exports,
  printing,jobs}` (registered, empty), `core/` (pure-processing boundary),
  `config/management/commands/validate_config.py` (moved to
  `apps/jobs/management/commands/` — Django discovers commands in installed
  apps; `--service web|worker` writability checks, RAW never probed).
- `.env.example` (no real secrets), `scripts/dev_env.{sh,ps1}`,
  `static/` + `staticfiles/` placeholders, README dev section updated.
- Tests (51): parser contract (profile default/invalid, DEBUG_MODE
  absent/TRUE/FALSE/mixed-case/whitespace/empty/invalid, secret file
  missing/empty/read, hosts required, loopback-only local bind, duplicate
  local roots, int/bool validation, architecture defaults), session
  settings (app boundaries, DEBUG=False, DB path, static/i18n), HTTP
  (healthz public 200 + loopback host, sanitized 500 without traceback,
  bad Host rejected 400), SQLite pragmas (foreign_keys ON, busy_timeout
  5000), `validate_config` subprocess tests (web/worker happy path,
  nas missing config fails loudly, DEBUG_MODE=TRUE still reports Django
  DEBUG False).
- Dependencies added and locked: whitenoise 6.12.0 (MIT),
  pytest-django 4.14.0 (BSD-3-Clause); `uv.lock` updated;
  `docs/LICENSES.md` verified from installed metadata.

**Actual local results** (Windows, uv 0.12.5, CPython 3.12.13):

| Check | Result |
| --- | --- |
| `uv lock --check` | pass (14 packages) |
| `uv sync --locked` | pass |
| `uv run ruff check .` | pass, 0 findings |
| `uv run ruff format --check .` | pass, 38 files |
| `uv run pytest` | 51 passed |
| `manage.py migrate` (local profile) | pass (auth/contenttypes/sessions) |
| `manage.py check` | 0 issues |
| `manage.py validate_config --service worker` (local) | pass, all roots writable |
| Live `runserver` 127.0.0.1:8765 | `/healthz` 200 `{"status": "ok"}`; bad Host header 400 |
| CI workflow | run 44724272495 success (job "Foundation (ruff + pytest)") |

**Notes / deviations:**

- Management commands are discovered from installed apps, so
  `validate_config` lives in `apps/jobs` (operations app), not `config/`.
- Tests run through `tests.settings` (re-exports `config.settings` after
  preparing a deterministic local test environment) because
  pytest-django imports settings before any conftest executes;
  `pyproject.toml` sets `DJANGO_SETTINGS_MODULE = "tests.settings"`.
- `Django OPTIONS` does not accept `foreign_keys` on the 5.2 SQLite
  backend; the pragma is enforced in `config/db.py` instead (tested).
- CI: run 44724272495 on the merged head passed (recorded in the table
  above).

## WP-03 — Authentication and session baseline

**Delivered** (branch `feature/wp-03-auth-session`, from `main`):

- `apps/accounts`: `models.LoginAttempt` (persistent rate-limit records,
  pruned after 24h) + migration 0001; `services.py` (login throttling:
  10 failures per (username, IP) in 15 min, case-insensitive username,
  per-pair, success clears history); `forms.py` (German labels/errors);
  `views.py` (login/logout/home; client IP from first X-Forwarded-For or
  REMOTE_ADDR; open-redirect guard via `url_has_allowed_host_and_scheme`);
  `management/commands/create_archivist.py` (interactive/random-password
  provisioning, no --password argument, username validation, password
  policy enforced).
- `config/settings.py`: explicit `AUTH_PASSWORD_VALIDATORS`
  (similarity/min-8/common/numeric); secure-cookie + SSL-redirect flags now
  derived from the new `env.secure_transport_required` (True in nas, False
  in local loopback) — a data-transport property of the profile, never a
  runtime toggle; `LOGIN_URL`.
- `tests/test_auth.py` (16 tests): unauthenticated root redirected to
  login with `next`, authenticated root available, healthz stays public,
  German login page; valid/invalid login (German error, session state);
  password stored PBKDF2-hashed; relative `next` honored, external `next`
  dropped (open redirect); logout; CSRF enforced on login and logout
  (403 without token, token round-trip succeeds); rate limiting
  (throttle after 10 failures even with correct password, success clears,
  old attempts ignored, per username+IP, case-insensitive); cookie
  contract (local flags off, nas env `secure_transport_required` True,
  always-on HTTPOnly/nosniff/DENY/LOGIN_URL/host validation).
- `tests/test_create_archivist.py` (6 tests): random-password creation with
  hashed storage and one-time display, duplicate rejection,
  set-password requires existing account, invalid username and weak
  password rejected (no account written).
- Test speed: `tests/settings.py` uses a low-iteration PBKDF2 hasher
  (dotted path, test module only) so the suite runs in ~3.5s; production
  settings keep Django defaults.

**Actual local results** (Windows, uv 0.12.5, CPython 3.12.13):

| Check | Result |
| --- | --- |
| `uv run ruff check .` | pass, 0 findings |
| `uv run ruff format --check .` | pass, 47 files |
| `uv run pytest` | 78 passed in 3.39s |
| `manage.py makemigrations --check` | no changes detected |
| `manage.py check` | 0 issues |
| Live runserver (real socket, curl) | `/healthz` 200 public; `/` 302 -> `/login/?next=/`; `/login/` 200 with CSRF token; bad Host header 400 |
| CI workflow | run 44736049991 on `8734c93` success (earlier run 44733254176 on `e3e8632` failed at Ruff lint; fixed by `8734c93`) |

**Notes / deviations:**

- Migrations are excluded from Ruff lint/format (`extend-exclude =
  ["*/migrations/*"]`) because Django's generated serializer does not
  follow the project style; this is standard Django practice.
- "Authorized browser login works" acceptance point is exercised through
  Django's test client (full middleware stack) here; a real browser smoke
  is the stated acceptance of WP-03a (Playwright), which will build on
  this baseline.
- No Playwright yet: browser tests arrive with WP-03a per the plan.
- CI run 44733254176 (head `e3e8632`) failed at the Ruff lint step: an
  unsorted import block in `tests/settings.py` introduced together with the
  test-only fast hasher. Fixed by `8734c93`
  (`fix(tests): sort test settings import block`); CI run 44736049991 on
  `8734c93` passed (job "Foundation (ruff + pytest)" success).

## WP-03a — Application shell and navigation

- UI-02/UI-03: German, translatable navigation, current page and visibly grouped
  unavailable modules. The home view explains availability for review, projects
  and jobs. Debug / Logs appears as a placeholder only in diagnostics mode.
  Keyboard skip link, visible focus, labelled inputs and login/logout feedback.
- Django collects the local stylesheet under its public static URL. No runtime
  asset dependencies. The browser test blocks external requests while retaining
  loopback access and checks applied CSS, keyboard navigation, failed and
  successful login, reload, disabled modules and logout.
- WP-03 follow-up: logout requires POST; throttling uses the direct peer and
  avoids validating credentials during lockout. Behind a proxy, attempts for
  the same username through that proxy share one limit.
- Follow-up audit (2026-11-20): confirmed PR #3 head and merge against GitHub,
  including successful CI run `44738003509`. Pushed the previously local
  browser database fix `400c44dc93fb6b953ee8c0fc45f4690b0ac6482a` to PR #4.
  Restored locked development dependencies locally: Ruff lint/format and
  82 unit tests passed on that head. Integrated current main without
  discarding either work package's progress record. Combined checks and
  browser acceptance are recorded after execution; NAS acceptance is open.
- After main integration: 90 unit tests, Ruff lint/format and the Playwright
  smoke passed locally. The browser test needed execution outside the network
  sandbox to reach its loopback-only synthetic Django test server. PR CI
  previously could not run on the conflicting branch; the progress-record
  conflict is resolved by preserving both packages' evidence.
- Final PR #4 head `557c1f517c14ca51458b6e1ddb73e4159c39a3df` passed
  GitHub Actions run `44747734412`, including the browser smoke. Merged as
  `e913d706d869de14f2e063eb0fb8b2835d548e98`; local main updated by fast-forward.

## WP-04a - Technical logging and mode contract

- Status: implemented locally on the WP-03 main baseline. OP-04 and GR-13
  use the shared mode parser and fixed web/worker roles. Both sinks encode
  allowlisted structured fields. Debug adds bounded, process-locked rotation.
- Five Python 3.12 unittest cases passed on Windows with synthetic logs,
  including restart persistence, retention, concurrent writer rejection,
  sanitized stdout/files and failure with an unusable output directory.
  Direct configuration probes passed for roles, paths and invalid settings.
- Python compilation and whitespace checks passed. The repository pytest
  suite and Ruff could not run locally because these packages are absent.
- GitHub Actions run `44746685234` on implementation commit
  `4ad1a389cb76f4c566835e24a281122fa6443572` passed on Linux: locked
  dependency sync, Ruff lint/format and the full pytest suite (including
  diagnostic tests and the Linux lock implementation). NAS acceptance
  remains outstanding.
- Owner authorization on 2026-11-20: merge PR #5 after successful checks;
  routine Git milestones within agreed scope no longer require repeated
  approval when checks/CI pass and no unresolved findings remain. Recorded
  in AGENTS.md and DEC-08. Documentation-only follow-up is included in PR #5.

## WP-04b — Authenticated debug UI

- OP-04: authenticated Debug-only page, JSON and download routes; Deploy
  rejects access even with historical files. Mode badge and usable navigation
  replace the former Debug placeholder. All responses disable caching.
- Fixed web/worker source IDs, validated job/level/component/time filters,
  source-bound signed cursors, rotation tracking and explicit lost-history
  reset. No arbitrary file path parameter or file mutation.
- Reader limits: 64 KiB / 100 records per page, 1 MiB / 1000 per download,
  4096-byte record fragments. Polling is sequential every two seconds,
  can be stopped, and retains at most 200 DOM rows. Files are re-sanitized;
  malformed, oversized, partial and non-regular/symlink inputs are handled.
- Local Windows / Python 3.12.14: Ruff lint/format, 110 pytest tests and
  2 Playwright tests passed. Browser coverage includes Debug auth/filters,
  live append, sanitized download, logout and offline local assets, plus
  the Deploy shell and direct-route denial. Synthetic data only.
- German archivist guide added. CI and NAS acceptance remain pending at
  this commit; no real association data or NAS operation was used.
- Final implementation head `e9df607b39d1f80409abf98e3b5d77717dd9b0a6`
  passed GitHub Actions `44749299835`, including both browser tests. PR #6
  merged as `ec705b29bc56d212cad1c34369cc5ba9dd9821c5`.

## WP-05a — Durable queue, claim and singleton worker

- OP-02: Job model and migration, payload version/size/domain validation,
  QUEUED/RUNNING/terminal transitions, progress, timestamps, cancellation
  intent and sanitized error codes. A migration seeds the unique worker lease.
- Atomic conditional ORM UPDATEs use short SQLite write transactions before
  reading candidates; no reliance on select_for_update. A partial unique
  RUNNING index and global lease prevent concurrent heavy claims. Worker
  generations and attempt numbers fence progress and completion.
- Lease expiry uses SQL execution time, not a timestamp captured before
  waiting for a write lock. An actual locked-connection expiry regression
  test verifies that a waiting claimant cannot revive an expired worker.
- Stable OS process lock beside the DB remains held even after lease expiry.
  Independent idle/busy heartbeat, 30-second leases, five-second renewal,
  freshness health command and bounded polling. SIGINT/SIGTERM stop new claims.
- Domain processors are deliberately installed by their own packages; only
  registered/validated payloads can enter the queue. No synthetic production
  jobs. No automatic retry or takeover of unfinished RUNNING jobs. Recovery,
  cancellation and fenced publication remain WP-05b; uncertain PRINT failures
  are REVIEW_REQUIRED and cannot re-enter the queue automatically.
- Integration uncovered that a Debug healthcheck would otherwise contend
  with the running worker's rotating log. Entry-point context now gives
  auxiliary management commands sanitized stdout only, preserving the shared
  mode and all security settings. The worker/web keep their file-writer rules.
- Synthetic acceptance: 30/30 competing Django-ORM claims over independent
  file-backed SQLite connections had exactly one winning worker/job. Also
  exercised duplicate same-lease claims, stale attempt/generation/expiry,
  idle/busy heartbeats, real worker CLI process-lock ownership, payload
  rejection, sanitized handler errors and PRINT uncertainty without retry.
- Final local checks (Windows, Python 3.12.14): `pytest -q` — 141 passed;
  Playwright browser suite — 2 passed; Ruff lint/format — passed (67 files);
  offline locked-dependency verification, Django system check, migration drift
  check and whitespace check — passed. Applied the migration and ran the real
  worker command against synthetic local storage. A separate real Debug worker
  and healthcheck coexist successfully without log-file writer contention.
- Owner requested completion, commit, push and then stop on 2026-11-20.
  Do not begin WP-05b or merge this branch without continuation. Linux CI
  and NAS/hardware acceptance are not claimed by local results.
- Later owner priority shift on 2026-11-20 explicitly resumed work for the first
  deployable preview. PR #7 head `960201c337ea1e0ae5095938dd7f6e330edcdee3`
  passed full Linux CI `44757097570` and merged as `5e6bacc816f69999bbe88eae11536cc2dee71da2`.

## First deployable technical preview — DEC-09

- Baseline inspection: clean WP-05a branch and clean `.dev/wp03a` / `.dev/wp04a`
  clones; all prior code preserved. WP-03a's browser transaction fix is already
  pushed, CI-verified and merged. No duplicate logging/UI implementation.
- 71 original packages (70 required, one optional). Seven are now fully
  software-verified/merged. Five deployment IDs and three early safety/operator
  slices form the preview path. Full worker/archive/hardware gates are retained;
  see DEVELOPMENT_SEQUENCE.md for the complete register and independent lanes.
- Implemented a web-only container/Compose candidate with protected empty or
  synthetic mounts, loopback-only HTTPS-proxy backend, explicit migration and
  interactive provisioning, persistent SQLite and a maintenance lock. Runtime
  does not auto-migrate or launch unfinished job processors. Placeholder UI is
  responsive, German, visibly unavailable and unable to modify archive data.
- Python image and build-only uv are digest-pinned; runtime Django updated to
  the verified 5.2.19 LTS security patch and Gunicorn 27.0.1 added/locked. Local
  locked runtime audit (pip-audit 2.10.1): no known vulnerabilities. Runtime and
  build/CI dependency notices updated from actual package metadata/license files.
- Local Windows checks at this snapshot: 165 pytest tests, two Playwright tests,
  Ruff lint/format and diff whitespace checks passed. Desktop/mobile screenshots
  visually inspected; no horizontal overflow. No local Docker executable exists;
  actual Linux image build, container smoke and image scan are pending GitHub CI.
- Workflow prepares checked image-artifact publication to GHCR, immutable version
  policy, registry pull/digest verification, signed provenance/SBOM and an install
  bundle/GitHub prerelease. No image availability, release or live NAS deployment
  is claimed before actual evidence. Actual main protection is absent; manual
  reviewed green-PR gate remains in force, without unapproved repository settings.
- Operator runbooks and German quickstart included. Actual DSM version, ACLs,
  certificate/proxy, resources and backup destination still require private
  authorized synthetic NAS acceptance. Real archive/member attachment is forbidden
  in this preview and has not been attempted.
- PR #8 implementation `0c2ff1d9487ae846e8d4826970904f6ad7c656ba`: CI run
  `44792816290` passed all Foundation checks and the actual Linux/amd64 image
  build. Compose validation failed at its model assertion: inactive tool
  services are correctly omitted by default. The follow-up explicitly checks
  both the web-only default and enabled tools profile; no safety/test is removed.
  Container runtime/restore/image scan remain pending this correction.
- Runs `44793166558` / `44793924558` passed Compose but showed no published
  port on the internal-only bridge while the web process was running. Docker's
  default-gateway port publication behavior requires a frontend attachment.
  The implementation preserves web's internal-only network and adds a bounded,
  mount-free TCP gateway from the same image; it has no private storage access
  and only forwards to fixed web:8000. CI now asserts that web has no default
  route and the gateway has no bind mounts; operator commands recreate both.
- CI run `44795938169` on `04c17e4895be6bea7ff806215d768279856e2f2c`
  passed Foundation, amd64 image build, Compose validation and the complete
  real-container/isolated-restore smoke. Trivy blocked publication with 101
  HIGH/CRITICAL findings in Debian 12 OS packages (zero Python-package findings).
  The follow-up uses the official Python 3.12.16 Alpine 3.24 base, pinned by
  registry-verified digest. Both build/runtime use the same musl base; all
  current runtime Python dependencies are pure Python. Future native packages
  must re-verify compatibility. No vulnerability exclusions or weakened scan.
- Startup now rejects known network/FUSE SQLite DATA filesystems before write
  probing; host preflight also rejects non-canonical secret paths.
- Alpine CI `44797068444` also passed build, Compose and complete runtime/restore
  smoke. Its scan found 16 HIGH findings, all in inherited `krb5-libs` 1.22.2-r1;
  Alpine's official 3.24 package index supplies the fixed 1.22.3-r0. The shared
  build/runtime base now installs that exact fixed version. Local checks after
  the storage changes: 170 pytest tests, Ruff (82 files), actionlint and diff
  whitespace checks passed. No scan finding is ignored.
- Final preview source `4aa216506f1fd4a37dfa3a35de519ed40e25ec34` passed
  CI `44797427059`: locked environment, Ruff, 170 Linux pytest tests, two
  Playwright tests, runtime audit, actual amd64 image build, default/tools/Debug
  Compose models, complete synthetic container/isolated-restore smoke, image
  vulnerability/secret scan and uploaded CycloneDX SBOM/image metadata.
  Trivy reported zero HIGH/CRITICAL OS/Python findings and no secrets. The
  full branch diff was reviewed; PR #8 has no submitted reviews or unresolved
  review threads at this checkpoint. Documentation-only follow-up records
  this evidence before the standing-authorized integration. No GHCR publication
  or NAS deployment has occurred. Nine packages are now software-verified;
  62 remain unfinished until WP-10's approved publication (then 10 / 61).

## WP-10 — First approved preview publication

- Owner explicitly approved `v0.1.0-preview.1` and GHCR publication on
  2026-11-20, following the reviewed PR #8 integration. No NAS deployment
  or real-data attachment was approved.
- Release source: `62d85b36189293a59df2ef39729a538f5c53ad3b` on main;
  final PR CI `44798017241` and main CI `44798414658` both passed.
- Annotated tag `v0.1.0-preview.1` was pushed and remotely verified against
  that exact source commit. Release run `44815669883` is the publication
  evidence checkpoint; completion and actual digest are recorded below only
  after registry/release verification.
- Original run `44815669883` passed all checks and pushed/pulled image digest
  `sha256:e6e01416737702598458af8c9167f2353e09074c445281d640eaa34f10658f4d`.
  Publication then stopped because `.RepoDigests[0]` still referred to the
  loaded `notenarchiv-ci` repository. Attestations/install release had not run.
- The correction selects the GHCR digest by repository and fails on absent
  or ambiguous results. Explicit recovery validates the original approved tag
  source, original workflow and all required successful check jobs; downloads
  the retained candidate with mandatory archive SHA-256 validation; and requires
  the existing registry version to match the candidate. It cannot rebuild,
  create a missing version, move a tag or overwrite a different image.
  Recovery signs a factual original-build/promotion predicate and the original
  SBOM; it does not mislabel the recovery commit as the application's build source.
  Local regression/policy checks: 27 tests passed, Ruff and actionlint passed.
- PR #9 source `6e3ce21e4230116d36557e0d44a2571e8ca5e43b` passed complete
  CI `44816957849` and merged at `24c3c8ea175b5c9d39df0813182cdbd39f55075b`;
  main CI `44817342191` also passed. Original tag and image stayed unchanged.
- Recovery run `44817372155` succeeded, including mandatory original artifact
  archive hash, equality with the existing GHCR image, authenticated image pull,
  signed original-build/promotion predicate, signed CycloneDX SBOM and GitHub
  prerelease/install assets. The exact reference is
  `ghcr.io/tostman1/notenarchiv@sha256:e6e01416737702598458af8c9167f2353e09074c445281d640eaa34f10658f4d`.
- Independent checks: anonymous registry manifest returned the same digest;
  all five downloaded release asset hashes matched GitHub metadata; all 12
  installation bundle files matched the original tag or digest file. Linux/
  amd64, non-root, version and source image metadata verified. `gh attestation
  verify` cryptographically verified both predicate types with the exact signer
  workflow/commit; their signed origin/SBOM claims match the release files.
- WP-10 is complete for this preview. Current count: 71 total, 10 software
  packages verified, 61 unfinished (60 required plus optional WP-43). Full
  worker/archive/operations gates remain; no NAS or real-data action occurred.
  See RELEASES.md for immutable digest, release/install URLs and evidence.

## Owner-authorized autonomous sequence — 2026-11-20

Three separate, sequential integration milestones: WP-05b/05c on
`feature/wp-05b-05c-job-management`, WP-11/12 on
`feature/wp-11-12-catalog-members`, then WP-17 on
`feature/wp-17-pdf-foundation`. Each starts from latest verified main after the
predecessor's complete acceptance, reviewed diff, green PR CI and verified
merge. Commit/push/PR/merge are authorized under the standing rules. Stop
after those three; no WP-13, archive/OCR expansion, release or NAS deployment.

### WP-05b / WP-05c local implementation

- Canonical OS-lock ownership authorizes successor recovery and worker-generation
  fencing, even when a dead predecessor's DB lease is still fresh. Old attempts
  cannot update state or enter the publication interface. Attempt history and
  delayed bounded retry policy persist in SQLite. PRINT never retries.
- Durable generic operation intents and domain reconciliation hooks surround
  short fenced final-publication callbacks. PENDING uncertainty requires evidence;
  unresolved effects block retries. No archive model/copy implementation is added.
- Cooperative cancellation, TERM/KILL POSIX groups and race-free Windows Job
  Objects stop owned descendants before terminal cancellation. Unverified cleanup
  requires review and stops the worker. PRINT cancellation/acceptance races remain
  REVIEW_REQUIRED without re-submission.
- Authenticated German paginated list/detail, progress, attempt history, explicit
  refresh, worker availability and CSRF-protected POST cancellation. No arbitrary
  submission, demo processors, raw payloads or exception text. Debug mode is not
  required. The published 0.1.0-preview.1 image is unchanged.
- Acceptance: actual worker process death between file effect and DB acknowledgement,
  reconciliation without duplicate publication, stale attempts, retry/backoff,
  PRINT uncertainty, 20 independent SQLite claim/cancel races, actual owned child/
  grandchild termination, and real browser cancellation of a running child process.
- Local Windows checks: 218 pytest tests, 3 browser tests; Ruff lint/format, Django
  system check, migration-drift check and diff whitespace checks passed. Actual
  Linux container CI and integration status are recorded in the subsequent checkpoint.
- Source `77d4f60d92c828ba407a89a180437e46ad72c0eb`, PR #11: full Linux
  CI `44823399459` passed Foundation, all browser checks, actual amd64 image
  build, Compose validation, real container/restore and vulnerability/secret scan.
  Full diff reviewed; no submitted PR reviews/unresolved threads at this checkpoint.
  Documentation-only follow-up records verified acceptance before integration.
  Current software-verified total: 12 WPs, 59 unfinished. No new image release.

## Owner extension and resumed milestone — 2026-11-21

The owner explicitly extended the session: finish the actual active WP-11/12
branch without discarding existing work; complete WP-17; then implement separate
`feature/synology-simple-install` with standalone `configuration.yaml` and a
concise primary German installation guide. Afterwards reassess and deliver the
next manageable dependency-ready manual archive slice when fully verifiable.
The earlier stop after WP-17 is revoked. Ordinary Git integration is authorized;
additional releases, NAS changes, real data and destructive production operations
remain unexecuted without their distinct approval. Preserve published preview assets.

- WP-05b/05c is actually merged via PR #11 at
  `470e7c8b0421d91ae38fbc65b888c16e70b1088c`; final PR CI `44823906492`
  and merged main CI `44824237705` succeeded. The merged tree matches the
  reviewed head. WP-11/12 starts from that verified base, not a duplicate job branch.
- WP-11/12 provides UUID catalog/member models, normalized canonical variants and
  part codes, explicit aliases with exactly one target, required protected member
  assignment, expected/optional parts and reusable independently copied templates.
  Unknown and deliberately defined empty expectations remain distinct.
- Complete authenticated German CRUD/search/pagination/detail screens include
  controlled references, explicit unused-record deletion, deactivation protection,
  optimistic conflict detection, CSRF and escaped output. Referenced musical
  identities cannot be silently retargeted. No archive files/roles are fabricated.
- Local acceptance: 265 full pytest tests, four Playwright tests, Ruff lint/format,
  Django system/migration-drift and whitespace checks passed. Separate interpreter
  migrations/reopen tests preserve identities/assignments. Browser acceptance covers
  equal titles/names, notation variants, template independence, member deactivation
  and protected references; desktop/mobile screenshots inspected.
- Full diff review, push/PR, Linux/container CI and verified merge remain the next
  gates. These source features are not claimed to be in the published 0.1.0-preview.1.
- Initial PR #12 source `32a7e065d9c1b8d562bbdc0d4b911fb56972e194` passed
  265 Linux tests and runtime audit in CI `44840283911`, but its mobile browser
  width assertion failed. Privacy-safe geometry diagnostics retained that exact
  assertion; full CI `44840633432` then passed, including all browsers and actual
  image/Compose/container/restore/security checks. An additional explicit load,
  font and animation-frame boundary removes the unsynchronized measurement after
  navigation/viewport resize. Final CI must still verify that follow-up.

- Final source `3f1b30969843f508ffda082c4f80d94155aff392` passed full CI
  `44841036938`: 265 tests, four browser tests, runtime audit, actual amd64 image,
  Compose, container/restore and vulnerability/secret checks. Full diff reviewed;
  no submitted reviews or unresolved threads. Software-verified count: 14 WPs,
  57 unfinished. Documentation checkpoint precedes authorized PR #12 integration;
  final PR CI and merged-main verification remain mandatory before WP-17.

- PR #12 merged at `a2d7264e43c823c612236e29effc414c8879cd97`; final PR CI
  `44841417182` and main CI `44841705128` passed. Merged tree equals reviewed
  head `c0d1a0af2e5cd72c5b4718412c9202e4c35a4645`. Local main: 265 tests passed.
- An additional Windows browser run exposed a concurrent job-test failure:
  Django's default shared-cache in-memory SQLite returned `database table is
  locked`. That mode does not exercise the production file DB busy timeout.
  A bounded follow-up uses an isolated temporary file DB for browser acceptance,
  and asserts that the real worker uses its canonical lock. No production DB
  settings, retry policy or browser assertions are weakened. Complete browser
  and CI gates must pass before starting WP-17.
- Follow-up local checks: all four browser tests passed; the real job lifecycle
  then passed twice independently. Ruff lint/format and whitespace passed.


## WP-17 — PDF foundation, 2026-11-21

- Resumed WP-11/12, completed PR #12 and its bounded browser test correction
  PR #13 before starting PDF work. PR #13 source
  `974348995e70ed97d8fe6eca57e300c4b547b802` passed CI `44842205008`, merged at
  `2f4b0e98bd81e4eff29b5c1326199f95c684986b`; main CI `44842489941` passed.
  Both merged trees matched reviewed heads. Catalog/member acceptance is integrated.
- Checked branches/worktrees/clean status and started
  `feature/wp-17-pdf-foundation` at that verified main. No duplicate PDF branch.
- Added locked pypdf 7.1.1 and pypdfium2 5.15.2; actual official Windows/musl
  wheels, hashes and native notices inspected. Alpine baseline is preserved.
- Pure core API accepts immutable byte snapshots, stages privately, and isolates
  every parser/native operation with memory/CPU/time/output limits. Adds bounded
  inspection/text, geometry/CropBox/UserUnit/rotation, thumbnails/PNG and ordered
  vector-preserving merge. Source/CLEAN bytes are untouched; no archive UI/OCR,
  approval, publication or generation feature is claimed.
- Reviewed active-content removal without losing Type3 glyphs/transparency.
  Unsupported visual annotations/forms fail explicitly rather than losing notation.
  Synthetic tests cover malformed/encrypted/oversize files, every major resource
  bound, compressed expansion, Unicode, A4/A3/custom rotations, effective crop,
  cancellation/private cleanup and structural/pixel preservation. A container smoke
  now exercises actual musllinux native PDF rendering in the hardened image.
- Intermediate local full suite: 316 passed, two POSIX-only skips on Windows;
  final form/active-content refinements and complete final gates are checked below.
  No Docker runtime is installed locally: image/Compose/security and Linux rlimit
  acceptance require GitHub CI. No NAS, real archive or additional release action.

- Final local full suite: 317 passed, two POSIX-only skips on Windows. All four
  Playwright browser tests passed. Latest parser/form refinements additionally
  passed targeted checks. Ruff lint/format (117 files), compilation, system,
  migration drift, locked dependency and whitespace checks passed. Full source
  diff reviewed. Synthetic PDFium and independent Poppler images visually checked
  (Poppler reported unavailable unused fallback fonts; the inspected German
  text/lines were intact). PR/Linux/container gates remain before completion.

- Source `309081c77ca296da1bdb8e1b13704da1c5aecc91`, PR #14, passed complete
  CI `44844708708`: 319 Linux tests (including POSIX gates), four browsers,
  runtime dependency audit, actual amd64 image/Compose/container/restore and
  native musllinux PDF primitives. Vulnerability/secret scan passed. No submitted
  PR reviews or unresolved threads; full diff reviewed. Software-verified count:
  15 WPs, 56 unfinished (55 required plus optional WP-43). Verify final docs CI
  and merged main before beginning the separate installation milestone.


## Simplified Synology installation — 2026-11-21

- Completed WP-17 before starting: PR #14 final head
  `27f77f8d390cf76b181fa5805f42c04e5026ddfd`, CI `44845116222`, merge
  `c12e71cc7c3d5676a5be5a4cadee1a39e6ea8cfc`; main CI `44845475304` passed.
  Merged tree matched the reviewed head. Current verified/integrated count:
  15 WPs, 56 unfinished. Published image/tag/assets remain unchanged.
- Checked root/status/worktrees/existing branches, then started separate
  `feature/synology-simple-install` from that verified main.
- Standalone `configuration.yaml` uses the published immutable digest, three
  essential edits (identity/host/origin), a fixed root with distinct subdirectories,
  no `.env` or new parser/service. All runtime protections/profiles remain.
- Guarded POSIX preparation creates only missing directories/key, validates
  actual non-admin identity/membership, canonical paths and existing modes, never
  recursively changes permissions, and refuses new keys beside existing DATA.
  Host preflight now checks RAW ownership and ancestor rename boundaries, including
  sticky-parent semantics, plus secret directory replacement denial.
- German primary guide follows eight actual first-start steps; README is concise.
  Technical diagnostics/developer/worker details were consolidated into appropriate
  docs, including correcting the obsolete pre-recovery worker description. Update,
  restore, Debug and advanced `.env` instructions distinguish the active base file.
- Future bundle packaging includes the new files and bakes the verified release
  digest into simple references without installer preprocessing or source changes.
  Historical packaging and original published assets stay unchanged.
- Local checkpoint: full pytest 321 passed / two POSIX skips, four browsers passed;
  bundle coverage expanded afterward to six passing focused tests. Ruff (120 files),
  compilation, actionlint and Bash syntax passed. Actual Compose parsing and
  root/Linux helper/container tests cannot run locally (no Docker); new CI exercises
  the published digest, real interactive provisioning, migration/restart persistence,
  host/container RAW denial, identity/mount/network limits, key preservation and
  negative preparation cases. CI has not yet run for this milestone.
- Physical DSM/Container Manager UI/ACL/TLS/firewall/filesystem/restore acceptance
  remains unperformed and separately authorized. This ops slice does not mark full
  WP-48/07/22 or other hardware-dependent packages complete. No real data or NAS use.

- Final local suite after bundle drift coverage: 323 passed, two POSIX-only skips;
  four browsers passed. Six bundle tests pass. Ruff/format, compilation,
  system/migration drift, actionlint, Bash syntax and revised local documentation
  links passed; complete diff reviewed. CI runs the first-install procedure with
  both the published immutable digest and the local candidate (no publication).
  Linux/Compose/container verification is still pending before integration.

- Source `c74e7c20ce1ee4348b6bc6e265d5517b88f2a820`, PR #15, passed full
  CI `44848131876`: 325 Linux tests, four browsers, runtime audit, actual image,
  Compose, container/restore/native PDF checks, and complete simple installation
  with both published digest and current candidate. Interactive account/password
  concealment, RAW negatives, persistence, key/data preservation and preparation
  refusal cases passed. Vulnerability/secret scan passed. Full diff reviewed;
  no submitted reviews/unresolved threads. Final docs CI/merge/main remain before
  advancing. Physical NAS gates remain separate; package count stays 15 / 56.


## Manual archive sequence — resumed 2026-11-21

- Owner reaffirmed: finish current installation first, then separate dependency-safe
  WP-13 and WP-14, continuing toward preview/index/review/search/download where
  complete acceptance and manageable integration permit. No automatic stop after
  WP-13/14, no OCR/project/printing prerequisite unless the plan requires it.
- PR #15 final head `d2dff42303f73728e75a44eed83dad235ebad5f0` passed full CI
  `44848528982`, merged at `480514264eee4aab15e77cc58447019d3a637154`; merged
  main CI `44875615555` passed. Trees match; simplified installation is integrated.
  Physical NAS acceptance and further releases remain unexecuted/unapproved.
- A local installation archive was built and inspected without publication:
  `.dev/notenarchiv-simple-install.tar.gz`, SHA-256
  `5e2c8f7f425412de4e05a0a5e2ad33ed24852c211985980869de523be26d7196`.
  It contains the exact published digest and all 14 intended regular files.
- Root/status/worktrees/upstream/existing branch were checked, then
  `feature/wp-13-archive-versions` started from verified main above. Archive app
  has only its skeleton; no implementation is assumed. WP-13 is now in progress,
  not complete. Counts remain 15 software-verified WPs / 56 unfinished.


## WP-13 � Archive versions and state model

- Separate branch from verified main `480514264eee4aab15e77cc58447019d3a637154`.
  Added protected source/file/version identities, separate base/derivative content,
  multiple part assignments, non-exclusive folder proposals, bounded local
  recognition evidence, sealed review revisions, exact per-reviewer inspections,
  audit history and job/attempt/intent-bound publication metadata.
- Short write-first services preserve approved assignments during new analysis,
  enforce explicit inspected approval and canonical receipts, reject stale edits,
  and retain withdrawn/unavailable history. Source/index/candidate/review/CLEAN
  availability are independent; no confidence-based auto-approval.
- 47 focused tests passed, including actual migration/reopen persistence,
  competing file-SQLite connections (one saved edit, one revision conflict),
  protected references, invalid states/paths/metadata, multi-part confirmation,
  stale/foreign proof, failed/wrong receipts and rollback. Four existing browser
  tests passed. Ruff lint/format (129 files), system and migration drift checks
  passed. Full regression suite and CI/integration remain in progress.
- See ARCHIVE_MODEL.md for contracts. No physical copy, ingestion, review UI or
  NAS validation is claimed by this model package. Counts remain 15 / 56 until
  full acceptance and green integration complete.

- Full regression after correcting the jobs-only SQLite test fixture: 370 passed,
  two POSIX-only skips. All ten real queue/recovery tests passed using the actual
  migrated schema; assertions and PROTECT constraints remain intact. Final diff
  review added explicit derivative approval coverage: derivatives require their
  own hash inspection and canonical publication in PROCESSED, never inherit base
  approval; all 17 workflow tests passed after this refinement. Existing four
  browser tests passed. Ruff, compilation, system/drift and whitespace checks
  passed. Ready for separate commit/PR and actual Linux/container CI.

- Source `2c91b43c06f989c205980e1acc99f84d4a8f5842` pushed on
  `feature/wp-13-archive-versions`, PR #16. Final focused suite: 48 passed.
  Full Linux CI `44881080792` passed: 373 tests (including both POSIX gates),
  four browsers, runtime audit, actual non-root amd64 image/Compose/native PDF,
  container and isolated restore, published/candidate simple first installs,
  vulnerability and secret scans. Complete diff reviewed; no submitted PR reviews
  or unresolved threads. This checkpoint precedes final documentation CI and
  exact-head integration/main verification. Integrated count remains 15 / 56
  until that gate; WP-14 has not started. No physical NAS/release action.


## WP-14 � Safe file publication (in progress)

- WP-13 final head `f9e2b281a8b17cccd4b389f613014fce5d3d98bf`, final CI
  `44881432325`, merged at `a480a2a11bed574ef098d37fb8c4b6a2961f9874`.
  Main CI `44881714517` passed; exact merged tree matched. Post-merge 48 archive
  tests, Ruff and system/drift checks passed. Counts: 16 integrated/software-
  verified WPs; 55 unfinished (54 required plus optional WP-43).
- Root/status/worktrees/upstream/existing branches checked; separate
  `feature/wp-14-safe-file-publication` starts from that verified main.
- Implementing descriptor-anchored read-only source access, bounded verified
  staging, PDF validation, no-clobber publication, SMB-safe naming/collisions,
  actual durable worker effects and recovery. A small job-framework prerequisite
  adds fenced pure DB metadata and transactional receipt acknowledgement during
  both normal publication and successor recovery. No real data/NAS/release use.
- Physical publication requires POSIX no-follow/dir-fd primitives. Unsupported
  platforms fail closed; Windows naming/metadata tests do not substitute for
  mandatory actual Linux CI/container publication tests or private NAS gates.

- WP-14 implementation checkpoint: real registered ARCHIVE_PUBLISH handler,
  verified independent staging/canonical copies, protected target reservation,
  exact retained-inode recovery and bounded temporary cleanup. Added pure DB
  receipt acknowledgement to the current worker fence, including cancelled
  recovery; known pre-publication refusals abandon intent, ambiguous effects do
  not. NAS worker command validates identity, storage and migration readiness.
- Local full suite: 386 passed, 36 POSIX-only skips (34 new physical publication
  cases plus the existing two); four browser tests passed. Ruff/format (137
  files), compilation, system/migration drift, actionlint and whitespace passed.
  Latest POSIX durability refinements still require actual Linux execution.
- New Linux acceptance includes independent worker death during copy, after
  link, inside DB acknowledgement and after commit; stale owner, cancellation,
  unrelated replacement/equal hash, explicit multi-part canonical approval and
  withdrawal history. New actual hardened-image CI exercises non-root worker
  publication with no network and independent host/mount RAW denial. These
  essential gates are pending, not claimed passed. See FILE_PUBLICATION.md.

- First WP-14 source `df89c248a2e521d70db4f7f90ed5833b9f0094fc` is pushed;
  draft PR #17, CI `44885476030`. Linux ran all 422 tests: 413 passed, nine
  actual-worker scenarios stopped in the test driver because structured stdout
  logs were parsed as one JSON document. All 19 physical file primitive tests
  and the ordinary copy/canonical/collision scenarios passed. The driver now
  distinguishes a marked fixture result from real technical logs and checks
  crash exit codes without expecting a return value. Domain assertions remain.
  Full Linux/recovery/container rerun remains mandatory before completion.

- Corrected driver head `005e99a2e71a040d6862447a6831425571ed6cbe` passed
  full CI `44885786349`: all 422 Linux tests and four browsers, actual hardened
  image/Compose/container/restore/native PDF, both simple-install flows, runtime
  audit and security scans. The new non-root worker actually copied, independently
  verified, explicitly reviewed and canonically published a combined fixture with
  RAW unchanged; independent host/mount denial and network-none were exercised.
- Final naming review preserves part codes under long instrument labels and
  keeps notation variants separate. Large combined sets use a bounded count/ID
  filename while retaining every controlled assignment in the DB. Added two
  naming tests; all 48 targeted naming/workflow/fence tests passed. Pending-intent
  abandonment also checks its exact affected row. Final-head CI and complete
  diff/review/integration remain before WP-14 completion. Count stays 16 / 55.


## Owner-requested review checkpoint - 2026-11-21

- Stop after the pushed WP-14 checkpoint; no merge or next WP in this run.
- Reviewed implementation 3c38500a492801b4ab5b846fcf202ca462d3800d passed full
  CI 44886399016: 424 Linux tests, four browsers, Ruff/format, runtime audit,
  actual image/Compose/native PDF/container/restore, both installation flows,
  non-root network-disabled worker publication and vulnerability/secret scans.
- PR #17 remains an open draft. WP-14 is software-verified on its feature branch;
  integration/main verification and private NAS acceptance remain outstanding.
  Integrated count stays 16 / 55. Documentation-only HEAD CI is separate from
  the verified implementation run. See HANDOFF.md for the current checkpoint.

- Final handoff: documentation CI 44886873476 passed at 36a2d80.
  Owner-supplied AGENTS.md transfer gate is included in the final marker commit.
  Reused existing verification; no implementation changes or expensive test rerun.

## WP-19 — Filename and text-layer recognition

- Base: verified main `5874c7c49f39ef05b3c8599819861fa6c27d8bac` (WP-14 merge,
  PR #17; main CI `44897447951` passed, merged tree matched). Branch
  `feature/wp-19-recognition`. Parallel agent works WP-18 in a separate
  worktree/branch; WP-19 stays independent and does not touch preview code.
- `core/recognition.py` (pure, no Django): NFKC/whitespace/casefold
  normalization, German+English pitch classes, bounded roman numerals (1-999),
  combined part-code splitting (`II/III`, `1-2`, `2_3`), label parsing
  (instrument name + optional pitch + optional part code), numeric-or-roman
  part equality and the agree/consistent/conflict/insufficient source relation.
- `apps/archive/recognition.py`: bounded versioned `RuleSet` snapshot of the
  active catalog (works, work aliases, variants, parts, instrument aliases)
  hashed into the candidate `rule_version`; filename evidence (longest
  resolving word suffix is instrument+parts, leading words are the title);
  bounded heading-region text-layer heuristics (no OCR); PROPOSED/CONFLICT/
  UNKNOWN verdict with bounded reasons and confidence; `record_candidate()`
  persists immutable sealed `RecognitionCandidate`/`CandidatePart` rows and the
  file's independent `candidate_state`. Idempotent under the same rule set;
  rule changes keep history and add a new candidate. Never approves, never
  changes review/publication/assignment states.
- Contract: docs/RECOGNITION.md; traceability rows updated in
  DEVELOPMENT_SEQUENCE.md and README.

- Plan acceptance cases are covered by synthetic tests: exact/alias/unknown
  work matches; pitch disambiguation (Klarinette A vs Bb); instrument aliases;
  roman numerals matching digit parts; combined parts keep all parts
  (`Tuba 1-2`, `Posaune II-III`); Unicode normalization (full-width spelling);
  Posaune-1 vs Posaune-2 disagreement is a conflict; ambiguous instrument is a
  conflict; rule-version change records a second candidate without touching the
  first; candidates cannot auto-confirm (review/publication/assignment states
  untouched, no proposals created); candidate and part immutability; bounded
  excerpt. Local focused suite: 24 passed (8 core + 16 archive recognition).

- Open reliability issue (not fixed, not weakened): on the local Windows
  machine (OneDrive-mounted tree, loaded environment), full-suite runs of
  `tests/test_job_lifecycle.py` show an intermittent, rotating lease/timing
  failure (different test fails per run; always green in isolation and in the
  merged-head Linux CI runs 44886399016/44887606153/44897447951). It predates
  WP-19 (observed before this branch). Treated as a local-environment
  flake, not a product defect; no test was weakened or skipped.

- Pushed as `2b44d3b` (single commit on `feature/wp-19-recognition`), PR #19
  open against main. Linux CI 44939684382 passed at that head (full pipeline
  including container publication and browser tests). Main moved while the PR
  was open: WP-18 (secure preview) merged at e04905a; no file overlap with
  WP-19 (new modules plus doc rows only) and the PR stays mergeable.
   This was the pre-integration checkpoint. PR #19 subsequently merged at
   `8cedf7bf74a2583b2d078516ba5066c16ecf0381`; combined main CI 44943760201
   passed after WP-18 merge `e04905aca5a044ed355b8408deac127852ca76b1`
   (PR #18, its main CI 44910769120 passed). Current integrated count is 19
   verified / 52 unfinished, including the previously integrated WP-14. No NAS,
   release or preview-image action; published assets unchanged.

## WP-15 — Indexing and separate STATUS publication

- Owner-approved scope: implement WP-15 with synthetic acceptance, standard
  feature branch/commits/PR and actual CI; do not merge without explicit approval.
  No deployment, real association data or NAS modification is authorized.
- Verified clean primary main/local/remote base:
  `96443f9759ba54bff77e5c3971056c2db3026dcb`, main CI 44952066658 passed.
  WP-14, WP-17, WP-19 and WP-05c dependencies are integrated/software-verified.
- Backend selected/all recursive inventory, stable streaming hashes, PDF metadata,
  existing safe CLEAN publication, WP-19 candidates, durable per-entry checkpoints
  and independently fenced mirrored STATUS snapshots. No unreviewed music usable.
  See INDEXING.md. WP-16 UI and WP-27 full integrity tooling remain later packages.
- Baseline full Windows suite before changes: 428 passed, 39 platform skips,
  four queue/lifecycle timing failures. This repeats the recorded local issue;
  no test was weakened. Focused implementation/Linux acceptance remain pending.

- Final implementation `96103648ef850352bc96182a0d1a776197468a07` passed full
  GitHub CI 44953809320: 488 Linux tests (including real indexing inventory,
  copy/STATUS worker deaths, cancellation, confirmed-history reuse and exact RAW
  before/after checks), five browser tests, locked runtime audit, actual amd64
  image/Compose/container/restore/native PDF and worker publication, both synthetic
  installation flows, vulnerability/secret scans and SBOM upload.
- Local full regression: 435 passed / 51 platform skips before the final two
  Linux-only acceptance additions; current focused archive/index suite: 37 passed /
  14 Linux-only skips. All 42 queue/lifecycle tests also passed in isolation.
  Ruff lint/format (155 files), lock, Django system/migration-drift and whitespace
  checks passed. Earlier Windows timing failures and Linux integration failures
  remain recorded, not hidden: global/per-copy progress isolation was corrected
  and regression-tested; marker crash injection no longer changes API capability
  detection. No tests or security checks were weakened.
- Untouched historical PROGRESS.md bytes were compared against base `96443f9`,
  including its two legacy non-UTF-8 heading bytes, and preserved exactly. No
  encoding repair was performed. Full branch diff reviewed; PR is mergeable with
  no submitted reviews at this checkpoint. This documentation-only follow-up has
  separate final-head CI. No merge, release, deployment or NAS operation occurred.
- Remaining risks/gates: actual NAS permissions/fsync/power-loss/resource behavior,
  single-writer managed roots, cooperative deadlines cannot interrupt kernel I/O,
  and non-atomic two-file STATUS mirror (JSON authoritative). WP-16 indexing UI,
  OCR WP-24/25, full integrity UI WP-27 and backup before real ingestion remain
  separate. Integrated count stays 19 / 52 until owner-approved integration.

## WP-16 — Indexing UI and approved continuous sequence

- Owner authorized conditional separate integrations: WP-15 merge, WP-16,
  WP-20a, WP-20b, WP-21; primary worktree only, no releases/NAS/real ingestion.
- WP-15 PR #21 head `5d7f5b5244c452c64784ac8a22a642cac58c635f` passed final
  CI 44954321633, merged at `3a5a69234ffa2762a4631d78bcc0e92a083ae1a7`.
  Merge tree equals reviewed head; main CI 44956825128 passed. Clean primary
  worktree then started `feature/wp-16-indexing-ui` from this verified main.
- WP-16 provides authenticated German folder overview/detail, selected/new
  RAW-relative and full-archive submission, existing job progress/cancellation,
  worker availability, pending-review counts/queue and mandatory inspection
  guidance. Complete integrity action remains explicitly unavailable until WP-27.
- Only exact APPLIED JSON receipts plus matching STATUS bytes and a completed
  successful scan prove STATUS publication. Text markers never imply successful
  indexing, approval or completeness. UI paths cannot choose arbitrary roots.
- Unit/integration/browser acceptance and final CI gates in progress. Review UI
  corrections/approval remain WP-20a; no auto-approval or deployment added.

- Implementation `2e8353a1c37e7d88129ad9bb23c1eb9ef3b2382e` passed full CI
  44958536579: 493 Linux tests, six browsers including real index/worker/STATUS
  and pending-review queue, runtime audit, actual image/Compose/container/restore,
  worker publication, installation flows and vulnerability/secret scans.
- Current local UI tests: five passed; all six browsers passed. Two full Windows
  runs each had 436 passed / 53 platform skips / four existing queue timing
  failures at differing cases; isolated queue/lifecycle suite had 42 passed.
  No assertions or security checks weakened. Ruff/system/migration/lock/diff checks
  passed. CI browser fixture now restores migration-seeded lease after test flush.
- Complete diff reviewed and historical document bytes preserved. Final docs-head
  CI/conditional merge/main verification remain before WP-20a. No NAS/release use.

## WP-20a — Individual review and publication

- WP-16 PR #22 final head `bbc708a0b1be861534814ceba63bbf130d186fd2` passed
  final CI 44959000193, merged at `4c75350b389a1b9b735be048b4cbd912b2c9f794`.
  Exact merged tree matches reviewed head; main CI 44959464054 passed. Clean
  primary worktree started `feature/wp-20a-individual-review` at that main.
- Implemented secure PDF.js review alongside immutable filename/text candidates,
  controlled arrangement/instrument/combined-part corrections, explicit per-account
  version/proposal/hash-bound visual inspection and separate durable canonical
  publication request. GET/preview never mutates review state; worker receipts
  alone complete availability and confirmed assignments. Audit/rejection retained.
- Existing preview exclusions remain: rejected/withdrawn files are not exposed
  through WP-18 routes. New manual correction can restore a rejected pending
  draft, but always requires a new inspection. No active-content/auth/CSRF/path
  boundary is weakened; RAW and historical copies remain immutable.
- Targeted local UI/preview/workflow checks: 55 passed / one POSIX skip before
  final browser acceptance. Full regression/browser/Linux/container gates pending.
  No OCR, preferred editions, project generation, NAS/release/deployment added.

- Final implementation `2122b51d15fe4cb4d5a42cf46297a564368c35eb` passed full
  CI 44961573223: 505 Linux tests, seven browsers, locked runtime audit, actual
  image/Compose/container/restore/worker publication, both installation flows and
  vulnerability/secret scans. HTTP review -> real worker death after link ->
  recovered canonical approval passed; RAW and controlled combined parts retained.
- All seven local browsers passed before the final form-ID fix; final review
  browser passed again afterward. Current focused review/workflow/preview suite:
  51 passed / one POSIX skip. Ruff/system/migration/lock/diff checks passed.
  Latest full Windows suite: 450 passed / 54 skips / one baseline queue timing
  failure. Latest isolated queue run was also affected (29 passed / 13 failures),
  despite earlier isolated successes. No local all-green claim or weakened test.
- Browser approval failure was duplicate checkbox IDs: explicit form-specific
  labels/IDs now preserve the separate attestations; server correctly rejected
  missing approval. Regression asserts unique IDs. Synthetic diagnostics never
  entered production error responses. Full diff reviewed; no PR review threads.
- Final documentation-head CI remains separate before conditional merge. Hardware
  gates, worker deployment/operations and backup before real data remain separate.

## WP-20b — Efficient review and batch approval

- WP-20a PR #23 head `c825c6e5ed261313f3fd2f5cda4f1575aa714e7f` passed
  final CI 44962136139, merged at `dc7892498428ce334841f0fdee4bbe3b7447cc58`.
  Exact reviewed tree matches; main CI 44962643794 passed. Clean primary worktree
  then started `feature/wp-20b-batch-review` from that verified main.
- Previous/next version navigation, persistent per-account inspection selection,
  signed one-hour actor/file/hash/proposal/revision/source-observation-bound tokens,
  explicit batch confirmation and bounded 25-file all-or-nothing metadata enqueue.
  Rechecks inspection/eligibility under a short SQLite write-first transaction;
  physical effects remain individual durable WP-14 operations. Same-name combined
  batch destinations are collision-planned, never overwritten.
- Uninspected/foreign/stale/changed/uncertain/duplicate selections reject the batch;
  no browser selection or preview counts as inspection. Unit rollback/auth/CSRF
  and actual browser multi-file acceptance added; Linux publication gate pending.
- Initial local focused suite: 22 passed; actual batch browser passed. Full
  regression, complete browser suite and GitHub/container CI remain pending.
  No OCR/preferred edition/project/export/NAS/deployment/release expansion.

- Final implementation `e1acf7844c28134dbeac1134c0d6e1681eb71446` passed full
  CI 44963862611: 520 Linux tests, eight browsers, runtime audit, actual amd64
  image/Compose/container/restore, worker publication, installation flows and
  vulnerability/secret scans. Two personally inspected same-name versions published
  to distinct canonical files; all-or-nothing metadata rollback was exercised.
- Current local batch suite: 15 passed; all eight browsers passed. Local full
  checkpoint: 459 passed / 54 POSIX/platform skips / four baseline queue timing
  failures. Ruff (172 files), system/migration/lock and diff checks passed.
  Import-format follow-up fixed without weakening assertions; no unresolved review
  threads. Final documentation CI and exact-head merge/main verification remain.

## WP-21 — Library search and completeness

- WP-20b PR #24 final head `c6d5c313039ab2783cbc41d150b1ed8e43cf25d4` passed
  final CI 44964388557, merged at `05a48983cdaac08e06ec46e682b1760ae31ee8b3`.
  Merged tree equals reviewed head; main CI 44964905107 passed. Clean primary
  worktree started `feature/wp-21-library-completeness` at this verified main.
- German authenticated local-only live title/alias substring search, NFKC/casefold,
  controlled arrangement/instrument/part/review/completeness filters and bounded
  lists. Independent expected-part/material overview, unknown/optional/required,
  confirmed/unreviewed/missing states; no automatic candidate approval or edition
  preference. Actual confirmed edition bytes hash-checked before preview linking.
- Existing expected-part/template CRUD and independent template application reused.
  Current manual proposal supersedes earlier recognition suggestions; confirmed
  history remains usable independent of new pending corrections.
- Synthetic unit/browser acceptance, Ruff/system/migration/full regression and
  GitHub/container CI gates in progress. No WP-23a/export/OCR/project expansion,
  real archive ingestion, NAS access, release or deployment performed.

- Final implementation `0f8639d8f28a87c176aa3157316f192b928248dd` passed full
  CI 44966827522: 530 Linux tests, nine browsers, locked runtime audit, actual
  amd64 image/Compose/container/restore/native PDF, worker publication, both
  synthetic installation flows and vulnerability/secret scans. Current library
  suite: ten passed. All nine local browsers passed before final grouped-query
  refinements; later library tests passed after those refinements.
- Local full checkpoint: 473 passed / 54 platform skips / one baseline queue
  timing failure. This is not an all-green Windows claim; the prior failures and
  intermittent isolated successes remain documented. No tests were weakened.
  Ruff lint/format (178 files), Django system/migration-drift, lock and whitespace
  checks passed. Complete diff/security review: no blocking finding, no submitted
  PR reviews or unresolved review threads at this checkpoint.
- Library overview/completeness uses stored relational eligibility, explicitly
  labelled as archive status rather than a full integrity proof. Displayed concrete
  editions additionally check receipt and actual managed bytes; observed missing/
  corrupt editions are marked unavailable with no preview link. Unknown expectation,
  optional parts and pending recognition never become a confirmed assignment.
- Existing progress history remained byte-identical to the WP-21 base, including
  legacy non-UTF-8 bytes; no encoding repair. Final documentation-head CI, exact-head
  conditional PR #25 merge and post-merge main verification are the remaining
  integration gates. Stop after those gates; no next work package is authorized.
- Remaining technical/hardware gates: private NAS ACL/mount/fsync/power-loss/load,
  backup before real archive ingestion, full worker deployment/operations, later
  full integrity UI, kernel-I/O deadline limitation and two-file STATUS publication
  (JSON authoritative). Existing pinned CI actions emit Node.js deprecation warnings
  but all checks ran successfully; action upgrades are not part of WP-21.

## Approved sequence completed — 2026-11-22

- WP-21 PR #25 final head `c6e13c8eec3dc09db08e10af7856bc184dafc086` passed
  complete CI 44967842286 (530 Linux tests, nine browsers, full container/security).
  Merged at `eb6c542f4527c0836820e3d8b6085a27dcc57d62`; exact merge tree
  equals reviewed head. Post-merge main CI 44968360320 passed all checks.
- The prior documentation-head CI 44967430490 exposed a browser synchronization
  race: existing four rows were mistaken for the new query response. Acceptance
  now waits for page load and the actual applied query plus exact result count.
  No assertions were weakened. Final local library browser and 36 focused
  library/batch/review tests passed. Earlier Windows timing failures remain recorded.
- WP-15/16/20a/20b/21 are implemented, software-verified and integrated through
  distinct PRs #21/22/23/24/25. Every package's PR and merged-main CI passed before
  starting its successor. Only the primary worktree was used; no linked worktree,
  force push, branch deletion, release, deployment or real NAS/data operation.
- This final evidence-only follow-up updates the WP-21 register without rewriting
  historical bytes. Its own PR/head/main CI is a separate Git checkpoint; it does
  not change application code or the accepted software test results.
- Stop after this documentation integration. Recommended dependency-ready next
  milestones: WP-47a full archive backup/restore before real ingestion, WP-23a
  preferred archive editions, and independently WP-29 project model foundation.
  WP-23b direct downloads follows WP-23a; OCR/full integrity remain later work.
  None was started. Private NAS/hardware/backup/worker-operations gates remain open.


### Manual Codex-to-OpenCode recovery - 2026-11-26

The interrupted WP-06p implementation was preserved on
codex/windows-source-reader at
6cd6ee4ed952e482614981afbd24e51222a76ab4.

Full regression completion and exact-head CI remain unconfirmed.

The incomplete OCR prototype was preserved separately on
recovery/codex-ocr-prototype at
49477203ef9dfb7f93e9533b2334bcd563a4162b.

The original local stash remains intact.

This one-time manual recovery does not modify existing
governance, authorization, verification or handoff rules.

See docs/HANDOFF.md for the current transfer snapshot.
