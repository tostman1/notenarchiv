# Agent handoff — WP-14 file publication in progress

Date: 2026-11-21. Git/source and specifications remain authoritative.

## Authorization and verified base

Owner authorized routine complete implementation, commits, pushes, separate PRs
and reviewed green-CI merges. Finish each milestone before the next. Continue
WP-13 -> WP-14, then dependency-ready preview/index/review/search/download toward
a usable manual archive. The earlier stop after WP-17 is revoked. Keep one active
implementation milestone; do not substitute broad redesign or OCR/project/print.

No additional release, NAS/infrastructure change, real music/member data,
destructive production work, force push or security/architecture change has been
performed or newly authorized. Preserve all existing branches and integrated
clean .dev/wp03a/.dev/wp04a clones. Main protection returned API 404: enforce the
reviewed-green-PR gate manually.

- PR #15 is merged: final head d2dff42303f73728e75a44eed83dad235ebad5f0,
  PR CI 44848528982, merge 480514264eee4aab15e77cc58447019d3a637154,
  main CI 44875615555 passed; merged tree matched the reviewed head.
- Standalone configuration.yaml, guarded idempotent preparation, concise German
  guide and future release bundle packaging are integrated. Actual Linux CI
  passed 325 tests, four browsers, both published and candidate first-install
  flows, container/Compose/restore/native PDF and security scans. NAS/DSM UI,
  ACL, private TLS/firewall and physical restore/load acceptance remain pending.
- Local non-published install bundle .dev/notenarchiv-simple-install.tar.gz has
  14 regular files; SHA-256 5e2c8f7f425412de4e05a0a5e2ad33ed24852c211985980869de523be26d7196.
  Existing v0.1.0-preview.1 tag, digest and assets remain immutable/unchanged.
- WP-05b/05c PR #11, WP-11/12 PR #12 plus browser fix #13, and WP-17 PR #14
  are already integrated and CI verified. See PROGRESS.md for full SHA/CI records.
  Do not reimplement them. New source features are not in the released image.

## Current implementation

Current active branch: feature/wp-14-safe-file-publication, from verified main
 a480a2a11bed574ef098d37fb8c4b6a2961f9874 (PR #16 merged). Final WP-13 head
f9e2b281a8b17cccd4b389f613014fce5d3d98bf passed CI 44881432325; main CI
44881714517 passed; reviewed and merged trees match. Post-merge 48 archive
tests, Ruff, system and migration checks passed. Last fully verified pushed implementation is 005e99a2e71a040d6862447a6831425571ed6cbe
on this branch, draft PR #17. CI 44885786349 passed all 422 Linux tests, four
browsers, actual non-root worker publication, container/Compose/restore/native
PDF and published/candidate install/security gates. Remote takeover is possible;
review all commits since the comparison base. No competing worktree.

WP-14 now implements descriptor-anchored file primitives, safe naming and the
registered actual worker publisher/reconciler, with failure/crash tests. POSIX primitives are
required for physical effects; unsupported systems fail closed. Local full suite: 386 passed, 36 POSIX-only skips; four browser tests passed.
Ruff/format, compilation, system/drift, actionlint and whitespace pass. Mandatory
actual Linux CI/container publication tests passed at that verified source.
Final naming refinement adds two tests (all 48 targeted tests pass) and preserves
part codes with long labels, distinct variants and bounded large-set count/IDs.
Verify latest head CI/full diff and mark PR #17 ready before exact-head merge;
then verify main. Do not claim the latest refinement CI has passed until observed. No NAS or real files are involved.
The small job prerequisite adds fenced pure metadata transactions and a handler
acknowledgement hook in the same transaction as APPLIED receipt, including
recovery of cancelled jobs. This prevents a physical-effect/DB-ack gap.

### Previous WP-13 source checkpoint (superseded by integration above)

Active branch feature/wp-13-archive-versions, comparison base
480514264eee4aab15e77cc58447019d3a637154. Root/status/worktrees/existing branches
were checked before branch creation. Reviewed source 2c91b43c06f989c205980e1acc99f84d4a8f5842 is committed/pushed
on that branch; remote takeover is possible. PR #16 full source CI 44881080792
passed. No WP-14 branch or physical publication implementation exists.

Added source folder/file/version, archive base/derivative identities, direct
arrangement and multiple assignments, non-exclusive folder proposals, bounded
local recognition candidates, sealed proposal revisions, exact reviewer/hash
inspection, protected audit and job/attempt/intent-bound operation metadata.
Short write-first transactional services use revision CAS, preserve previous
approvals during new analysis, reject uninspected/stale/foreign evidence, and
require exact canonical publication receipts before confirmation. Withdrawal
retains bytes/history. Index, presence, candidates, review and availability remain
independent. See ARCHIVE_MODEL.md for the supported metadata API and WP-14 fence
requirements. No ingestion, file copy or user-facing review is claimed here.

Initial archive migration is newly generated and unapplied in the development DB;
no historical committed migration was rewritten. Focused metadata/persistence
suite: 48 passed, including actual migrations, independent file-SQLite competing
connections and interpreter restart/integrity. Four existing browser tests passed.
Ruff lint/format, Django checks and migration drift passed. Full regression found
two queue fixture errors: hand-created jobs-only schema lacked the newly protected
archive reference table during Django deletion collection. The fixture now uses
actual migrations; no production constraint or test assertion was weakened.
All ten queue/recovery tests then passed; full regression passed 370 tests with
two POSIX-only skips. Final derivative-approval refinement passed all 17 workflow
tests; derivative copies require their own exact-hash inspection and canonical
publication in PROCESSED. Ruff/compile/system/drift/whitespace checks pass.
Complete source diff reviewed. Full Linux CI 44881080792 passed 373 tests,
four browsers, actual image/Compose/native PDF/container/restore and both
simple-install image flows, runtime audit and vulnerability/secret scans. No
submitted PR reviews or unresolved threads. Final documentation CI, exact-head
merge and merged main verification remain before WP-14.

## Next action and counts

Finish WP-14 core/services, failure/recovery/negative and actual Linux/container
tests; review complete diff, document evidence and integrate separately only with
all acceptance and green CI. Continue the dependency-ready manual archive after
verified main; do not stop automatically after WP-14.

16 software-verified/integrated WPs; 55 unfinished (54 required + optional WP-43).
WP-13 is integrated. WP-14 remains in progress. Installation is
an ops slice, not full WP-48/07/22. No hardware gate is inferred from Linux CI.
