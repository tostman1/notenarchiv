# Agent handoff — active PDF foundation

Date: 2026-11-21. Git/source and repository specifications remain authoritative.

## Scope and authorization

Finish WP-17 on its separate branch, then feature/synology-simple-install.
The owner's extension supersedes the old stop after WP-17. Afterwards reassess
one manageable dependency-ready manual archive slice; do not implement the whole
suggested roadmap speculatively. Each milestone needs full acceptance, reviewed
PR, green CI, authorized merge and verified main before dependent work.

Ordinary development/Git integration is authorized. Additional releases, NAS
changes, real data, destructive production operations, paid services and changes
to architecture/security invariants retain separate approval. Defer those actions.
Published v0.1.0-preview.1 tag/image/assets remain immutable and unchanged.

## Actual checkpoint

- Active branch: feature/wp-17-pdf-foundation.
- Comparison base: 2f4b0e98bd81e4eff29b5c1326199f95c684986b, verified main.
- Current PDF source/docs are locally implemented; inspect uncommitted tracked
  and untracked files. Commit/push/PR/CI/integration remain mandatory.
- WP-11/12 resumed and completed through PR #12, merge
  a2d7264e43c823c612236e29effc414c8879cd97; head
  c0d1a0af2e5cd72c5b4718412c9202e4c35a4645, PR CI 44841417182,
  main CI 44841705128 passed. Full catalog/member German CRUD is integrated.
- Extra Windows browser verification exposed shared-cache memory SQLite locking.
  Browser acceptance now uses private file SQLite and the real canonical worker
  lock. All four browsers and two independent job tests passed locally.
  Follow-up PR #13 head 974348995e70ed97d8fe6eca57e300c4b547b802 passed full
  CI 44842205008, merged at the current base; main CI 44842489941 passed.
  Both merge trees exactly matched their reviewed heads.
- WP-05b/05c is already merged in PR #11 at 470e7c8, with PR/main CI green.
  No framework duplication. See PROGRESS.md for full comparison and evidence.
- Existing branches/worktrees were checked before creating WP-17; current
  checkout reused. Preserve existing integrated .dev/wp03a/.dev/wp04a clones.

## PDF implementation and checks

See PDF_CORE.md for API/limits and LICENSES.md for actual wheel/license evidence.
Locked pypdf 7.1.1 / pypdfium2 5.15.2 support amd64 Windows and musl; pinned Alpine
base remains. Input bytes are immutable, sources/CLEAN untouched. Pure core
inspection/text, effective boxes/UserUnit/rotation, bounded RGB PNG/thumbnail and
ordered vector-preserving page copy/merge run only in resource-limited child processes.
No OCR, archive model/UI, human approval or product export endpoint is invented.

Limits cover aggregate bytes, pages, pixels, geometry, text, decoding work,
output, scratch per invocation, memory/CPU/time. Caller owns authorization,
stable input reads, single-heavy-job serialization and durable publication.
Windows Job limits and POSIX rlimits precede native imports; existing owned-tree
cleanup/cancellation remains. Fixed errors never contain parser text. Merges
remove interactive document state while retaining Type3 glyphs/transparency;
unsupported visible annotations/forms fail rather than silently losing content.

Final full Windows suite: 317 passed, two POSIX-only skips; four browsers
passed. Latest parser/form refinements additionally passed targeted tests. Ruff,
compile, system/migration drift, lockfile and whitespace passed. Full diff
reviewed; PDFium/independent Poppler images visually inspected. Real process memory/CPU
limits passed; Linux permissions/file rlimit and actual musl image rendering are
CI gates. No local Docker is installed. Do not infer NAS acceptance from CI.

## Counts, release and next steps

Current fully software-verified/integrated count: 14 WPs, 57 unfinished (56
required plus optional WP-43). WP-17 counts only after complete remaining gates.
Main protection was unavailable (actual API 404); preserve reviewed-green PR gate.
Published preview source 62d85b36189293a59df2ef39729a538f5c53ad3b and exact image
are recorded in RELEASES.md. New source features are not in that released image.

Finish/review/test/push WP-17, open separate PR and resolve every CI failure.
Verify merged main before simplified installation: standalone configuration.yaml
using the immutable published digest, minimal essential edits, safe preparation,
primary concise German guide, advanced runbooks retained, actual Compose/container
and future release-bundle CI coverage. Never rewrite published assets or deploy
on NAS. Actual DSM/ACL/TLS/filesystem/load/restore evidence remains private,
unperformed and separately authorized. Synthetic development data only.
