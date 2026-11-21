# Agent handoff - WP-14 pushed review checkpoint

Date: 2026-11-21. Git/source and specifications remain authoritative.

## Owner instruction

The latest owner instruction supersedes autonomous continuation: finish the
current safe checkpoint, commit/push and stop. Do not merge or start another WP
as part of this run. The existing PR stays open for review. No NAS deployment,
real archive/member data, new release or destructive operation is authorized.

## Branch and comparison

- Branch: feature/wp-14-safe-file-publication.
- Comparison base / verified main: a480a2a11bed574ef098d37fb8c4b6a2961f9874
  (WP-13, PR #16; main CI 44881714517 passed).
- Reviewed and pushed implementation: 3c38500a492801b4ab5b846fcf202ca462d3800d.
- PR #17 is an open draft, not merged. Remote takeover is possible. Review the
  complete branch diff and all commits since the comparison base, not only HEAD.
- This documentation checkpoint follows that verified implementation; verify
  its actual pushed HEAD/available CI separately. No implementation changes follow.

## Implemented and verified

WP-14 supplies descriptor-anchored POSIX read-only source access, bounded
streaming copy, independent SHA-256/readback and isolated PDF validation,
SMB-safe names/collisions, no-clobber publication and actual worker recovery.
Retained stage/final inode evidence prevents adoption of unrelated replacements,
even with equal hashes. Explicit inspected canonical approval, cancellation and
withdrawal preserve history. Pure DB receipt acknowledgement shares the worker
fence. Unsupported physical filesystem APIs fail closed; no weaker Windows path
fallback exists. See FILE_PUBLICATION.md and JOB_FRAMEWORK.md for contracts.

Full implementation CI 44886399016 passed: 424 Linux tests, four browsers,
Ruff/format, locked runtime audit, actual hardened amd64 image/Compose/native PDF,
non-root network-disabled worker copy/review/publication, independent host/mount
RAW denial, container/isolated restore, both simple-install image flows and
vulnerability/secret scans. Local full regression: 386 passed, 36 POSIX skips;
final naming/workflow/fence refinements: 48 targeted tests passed. Four local
browsers, compilation, system/migration drift, actionlint and whitespace passed.
Complete diff reviewed; no submitted PR reviews or unresolved threads observed.
The earlier scenario stdout parsing failure was fixed without weakening domain
assertions; the subsequent full Linux/recovery/container runs passed.

## Remaining boundary

Stop here for owner review of PR #17. Integration and merged-main verification
remain unperformed. Indexing, secure preview and review/search/download UI are
later WPs, not claimed delivered by this backend package. Full worker Compose/
operations and actual NAS filesystem/fsync/ACL/TLS/load acceptance remain separate.
No known software defect remains in the verified checkpoint.

16 WPs are verified and integrated; 55 remain unfinished by that counting rule.
WP-14 is software-verified on its feature branch, not yet integrated. PR #15's
simple installation and WP-13 are merged. Published v0.1.0-preview.1 image/tag/
assets remain unchanged; newer source functionality is not in that image.

## Final transfer marker

Documentation checkpoint 36a2d80cb6cb7b82850b3449ba19eadf6dfff0c1 passed
CI 44886873476. The final transfer commit also includes the owner-supplied
AGENTS.md readiness gate. Verify its exact subject/trailer at remote HEAD;
its own CI is separate. No development, merge or next WP is authorized here.
