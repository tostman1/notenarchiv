# Development handoff — OpenCode to Codex

## Transfer snapshot — 2026-11-26

- Repository: `tostman1/notenarchiv`
- Transfer branch: `codex/windows-source-reader` (upstream same branch at origin).
- Comparison base: `ab172f6f942d5de743aec21aa6f0222caaa9798e` (integrated PR #61;
  exact Main CI `45694893160`). Review all commits/diffs since this base.
- Last implementation checkpoint: `d5460588c999251e5f98a4184538528029ddbaeb`.
- Pre-amendment documentation checkpoint: `65c94e1155b88fe86a197e42f9ed601be513c747`.
- Active PR: #62, open **draft**; unfinished, not merge-ready.
- WP-06p: partial; native writes disabled. WP-54: geometry preparation only,
  models/migrations/workflows not activated. WP-55 remains planned.

This snapshot is included in the final transfer commit. Its SHA cannot be embedded
in its own contents: obtain the exact final remote HEAD and verify the mandatory
AGENTS.md subject/trailer gate. A valid marker permits takeover, not a merge,
release, real-data migration, permission change or production deployment.

## Implemented and preserved

- Native read-only fixed-local-NTFS source reader: volume/file IDs, 100-ns native
  metadata, pinned validated traversal, namespace/reparse/hardlink rejection,
  read-only non-inheritable streams and conflicting write/rename protection.
- Backend-owned source selection, publication effects/proof, ownership and cleanup
  boundaries; POSIX behavior retained. Shared failure contracts and actual worker
  PENDING/REVIEW_REQUIRED regression preserve proof after injected effect failure.
- Opt-in read-only Windows token, descriptor, effective access and bounded recursive
  RAW-preflight evidence, scoped descendant/parent pins. **Always uncertified**:
  no production ACL/account provisioning or complete process/thread RAW enforcement.
- Immutable bounded source geometry/regions and invertible display transforms;
  original/effective CropBox and UserUnit/rotation fingerprint; opt-in lossless
  parser wrapper. Legacy PageInfo/inspection IPC unchanged. No region approval,
  resolver extension, source/content models or migration is claimed implemented.
- DEC-15 documentation amendment: revised storage authority/recovery, isolated
  processing scratch, proportionate acceptance and decoupled shared roadmap.

## Verification evidence and limits

Reuse results when code is unchanged; never apply older CI to a newer SHA.

- Exact PR #62 Foundation, Container and Windows checks passed at
  `d5460588c999251e5f98a4184538528029ddbaeb` via deterministic SHA-bound waiter.
  Earlier verified checkpoints are recorded in PROGRESS.
- Pre-amendment HEAD `65c94e1155b88fe86a197e42f9ed601be513c747`: all three checks
  observed completed SUCCESS, workflow run `45815589039`. No outstanding checks
  were observed before the documentation update.
- Final documentation/transfer SHA: CI is **not verified in this snapshot**.
  Publishing triggers CI; pending/new results must not be called green. No merge
  is planned and no expensive full regression rerun solely for this handoff.
- Latest geometry/source suites: 114 passed; bounded RAW preflight: 35 passed with
  native synthetic traversal; source/access: 72 passed with exactly two known
  privileged symlink-setup cases excluded in that focused run (assertions unchanged).
- Full local Windows regression earlier: 942 passed, 2 failed, 143 skipped;
  both failures were symlink setup WinError 1314, not passed assertions. Initial
  120-second run timed out, not successful evidence. Required CI subsequently
  passed on its Windows/Linux runners. POSIX-only skips are not local verification.
- Existing Ruff, Django/migration-drift, requirements/traceability and exact CI
  results remain valid within their recorded scopes. Documentation-task checks
  are recorded in PROGRESS. No native write/recovery or physical power-loss/NAS
  acceptance has been demonstrated. Process termination is application-crash only.

## Current owner decision and remaining work

Read DEC-15 and amendments to REQUIREMENTS, ARCHITECTURE, IMPLEMENTATION_PLAN,
PORTABILITY and TRACEABILITY. It partially supersedes DEC-14: immediate durability
of every parent creation/rename/disposable recovery deletion is no longer an
unconditional release blocker. Missing platform documentation is not an observed
failure; prior speculative namespace analysis must not be restarted as a gate.

Retain independent OS RAW denial (dedicated non-admin, non-RAW-owner Windows
identity/read-only NTFS; Linux least privilege/read-only mount), protected SQLite
and confirmed history, real hash-identical CLEAN, no-clobber and safe paths. CLEAN
may be the last historical copy. Acknowledged external files may require detection,
reconciliation or exact-input reconstruction after abrupt power loss; unavailable
or corrupt references cannot silently remain valid. Uncertain/unknown ownership
requires evidence-preserving review, not blind mutation retry.

Next cohesive implementation tasks:
1. Reassess remaining WP-06p under DEC-15. Reuse native code/backend interfaces;
   prefer simple established no-clobber staged publication and existing persistent
   operation records. Implement/verify file/DB failure-window reconciliation,
   missing-result detection/reconstruction and historical-copy protection. Do not
   add another DB/journal/service or enable Windows writes prematurely.
2. Formalize/reuse bounded job-owned scratch and physical hash-verified isolated
   processing inputs, source-change checks, immutable snapshot reuse and safe
   abandoned cleanup. Protect active workspaces/uncertain proof; disposable cleanup
   normally warns. No writable RAW paths/hardlinks; pure hashes/enumeration need
   no extra copy. These obligations are not retrospectively marked satisfied.
3. Verify independent RAW denial across application roles with reader handles
   closed. Production identity/ACL provisioning and administrative synthetic
   facilities need their applicable explicit authorization; never modify real data.
4. Continue platform-independent WP-54 additive model/backfill/legacy compatibility
   and WP-55 hierarchy/editions when shared dependencies are met. Remaining native
   Windows write acceptance, production security and packaging do not block them.
   Preserve migration/restore/history, resolver and revision-bound review gates.

Acceptance targets include RAW unchanged/OS-denied writes, physical copy/hash
equality, mutation/interrupted staging/publication, DB/file reconciliation,
reproducible reconstruction, last historical CLEAN retention, scratch/active/proof
cleanup safety, collision races and bounded Windows/Linux parity. Details remain
in canonical package/traceability documents, not a new test certification here.

## Preserved OCR recovery material

- Remote branch: `recovery/codex-ocr-prototype`
- Verified remote SHA: `49477203ef9dfb7f93e9533b2334bcd563a4162b`

Contains incomplete `core/ocr.py` (including unresolved `_region()`), dependency
and lockfile changes. Recovery reference only: assess reusable pieces at OCR work,
never blindly merge/cherry-pick old dependency/lock changes. No access to an old
machine stash is required; no recovery branch/artifacts were deleted or changed.

## Codex takeover instruction

Inspect local status and safely fetch `origin/codex/windows-source-reader` before
switching or editing. Latest remote HEAD must have exact subject
`chore(handoff): prepare agent transfer` and trailer `Handoff-Ready: yes`; otherwise
stop as required by AGENTS.md. If valid, read AGENTS/HANDOFF/PROGRESS and DEC-15,
review all commits/diffs from the recorded base and verify actual CI state.
Continue the revised roadmap autonomously with cohesive delivery packages, bounded
delegation, existing deterministic tools and exact-SHA PR/post-merge Main gates.
Preserve deferred features and all security/integrity/review/release gates. Do not
merge unfinished PR #62. OpenCode stops after this verified transfer.
