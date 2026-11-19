# AGENTS.md — Coding agent instructions

## Mission

Build the local German-language Notenarchiv & Marschbuch-Generator for a Synology DS224+. This is an independent application. Use the repository documents as the project context; do not start a new general design exercise every session.

## Authority and scope

- `REQUIREMENTS.md`: binding functional and non-functional requirements (stable IDs).
- `ARCHITECTURE.md`: technical target and invariants.
- `DECISIONS.md`: confirmed product decisions, recommended defaults and actual evidence still needed.
- `IMPLEMENTATION_PLAN.md`: work packages, dependencies, acceptance and release gates.
- `README.md`: overview, not a conflicting specification.
- The latest explicit owner decision takes precedence over older conflicting user-level project instructions. Record approved changes in relevant documents. Do not silently change requirements.

Verify Git repository root (`git rev-parse --show-toplevel`) before writing. Work within that root using relative paths. Inspect current branch, status and diff; preserve existing unrelated user changes. Do not use global OpenCode folders as the project workspace. External files may be read or copied only when appropriate and permitted; external modifications need approval. Respect tool permissions; never bypass them.

## Working behavior

1. Continue from the actual repository state. Read relevant specification sections and the selected work package before making changes. Do not assume planned functionality exists.
2. Work independently within the approved task. Make reasonable reversible technical choices, document material deviations and ask only for genuinely blocking scope, architecture, security or data-integrity decisions. Do not reopen resolved questions or repeatedly debate permissions.
3. Implement the requested package in small coherent increments. Add required dependencies when the approved package needs them, update the lockfile, and avoid unrelated refactors or needless infrastructure. If blocked, complete independent work and report the specific blocker.
4. Use tests, linters and inspection as appropriate. Fix causes rather than weakening tests. Never claim a test, build, NAS operation or deployment ran if it did not. Do not mark an incomplete package done.
5. Large file writes: use coherent small edits/chunks (approximately 5,000 characters or less where tool reliability requires it), verify each write and final file contents. Recover from malformed tool calls; do not restart planning because a write failed.
6. Keep progress concise: actual changes, checks, results, remaining issues. Propose the next logical action rather than generating another long alternative plan.

## Approvals and milestones

Documentation can be updated as part of an approved documentation task or to reflect an approved implementation. For a meaningful next implementation package, commit, push, PR, merge, branch deletion, release or deployment, propose the action, explain what is ready, give the commit message/tag where relevant, and request approval. After approval, execute the specified action directly without redundant confirmation. A previously approved action within the same scope does not need repeated permission. Do not treat these operations as permanently prohibited. Approval for a documentation task is not approval for unrelated implementation, external infrastructure changes or deployment.

Use feature branches from `main` unless the owner selects another active branch. Small English Conventional Commits. Never force-push or discard user changes without explicit approval. Report if CI or branch protection is unavailable rather than fabricating it.

## Invariants (must survive every change)

- RAW strictly read-only at NAS and mount; even marker files go into separate STATUS. CLEAN copies are real, byte-identical, hash verified; PROCESSED derivatives separate. No blind overwrite or deletion of historical referenced files. Every new/changed PDF inspected and manually approved; no filename/OCR confidence auto-approval; unchanged confirmed hashes reusable.
- Index, review and completeness are distinct. Batch confirmation only after explicit visual review of each version. Unconfirmed/withdrawn versions are not used in new exports.
- One shared list per project, automatic numbering with explicit reserve slots, no personal omissions/additions. Full folders only per participant. Excerpts, direct archive notes and contents-only are independent output types. Never print piece numbers onto music pages.
- Project default is saved, not a live member default. Personal overrides are easy, persistent and win over defaults. Ensemble role differs from playable part. Explicit compatible edition wins; only use confirmed versions, and never silently substitute an available manual choice. Missing music requires acknowledgement and placeholder.
- One resolution engine for matrix, preflight and generation; immutable snapshots and pinned inputs, no hidden mutations of previous output. A3 native pages never split; pair only consecutive A4 portrait pages within a single piece. No automatic print retry after uncertain submission.
- Local only; never send actual association notes, members, OCR text, credentials or DB to external AI, Git, CI or logs. Synthetic deterministic fixtures for development/CI. Real validation only privately on the NAS.
- `DEBUG_MODE` absent or FALSE => Deploy; TRUE => application diagnostics; Django DEBUG always False. Auth, CSRF, safe paths, non-root and all other safeguards stay active. Never disable security to make a test pass.

## Engineering conventions

English technical documentation, code, comments, identifiers, tests, log messages and commits. German UI and archivist manuals; use i18n-aware user strings. Python 3.12/Django 5.2 LTS baseline, uv lockfile, Ruff and pytest; use supported pinned versions. Pure processing in `core/`, domain logic in services, thin Django views. SQLite-specific atomic updates and short transactions; one heavy worker, durable operations, idempotent recovery. Keep bounded memory, time and scratch use. No unnecessary services, SPA or external assets.

## Definition of done

For each package: relevant requirements implemented; acceptance tests exercised and recorded; lint/test results actual; docs/traceability updated; Git diff reviewed; no unrelated changes, private data, secrets or unverified claims. Report status as planned / in progress / implemented / verified / blocked. Distinguish local success from NAS/hardware acceptance and CI success. Then recommend the next milestone and ask for approval where needed.
