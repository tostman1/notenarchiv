# Agent handoff — latest preview snapshot

This snapshot supersedes the old WP-03 transfer record. Repository files/Git
remain authoritative; inspect the complete comparison on takeover (AGENTS.md).

## Git checkpoint

- Date: 2026-11-20; agent: Codex.
- Current branch: `codex/first-deployable-preview`.
- Comparison base / last committed head at this snapshot:
  `5e6bacc816f69999bbe88eae11536cc2dee71da2` (PR #7 merged into main).
- Intended transfer ref: `origin/codex/first-deployable-preview`.
- Preview implementation is currently uncommitted and not pushed; no future
  commit SHA is asserted. Remote takeover of this preview is not yet possible.
- Other clones: `.dev/wp03a` and `.dev/wp04a` are clean and their implementations
  are already integrated. Preserve them; no branch/worktree deletion is approved.

## Verified baseline

WP-01/02/03/03a/04a/04b/05a are software-verified and merged. WP-03a's original
Playwright DB-access failure was fixed by `400c44d`, integrated at `557c1f5`,
verified in CI run `44747734412` and merged in PR #4. WP-04a is in PR #5;
WP-04b in PR #6 (CI `44749299835`). WP-05a is in PR #7 (CI `44757097570`).
No worker is deployed by the proposed first preview. WP-05b remains planned.

## Current authorized work

The owner's latest priority shift authorizes the first empty/synthetic-data
web-only technical preview, not real archive access or a live NAS deployment.
DEC-09 and IMPLEMENTATION_PLAN.md record its scoped dependency/order changes.
WP-09/06/07/08/10 and early WP-47a/48/49 slices are grouped into one coherent
preview branch. Full package gates remain in DEVELOPMENT_SEQUENCE.md.

Implemented: Dockerfile, Compose web/tools, root/mount/secret/identity guards,
explicit migration/provisioning, guarded Gunicorn, honest responsive preview
UI, extended CI/security/SBOM, approved-tag GHCR pipeline and operator runbooks.
The image has not yet been built/published at this snapshot.

## Actual checks and open gates

- Local Windows / Python 3.12.14: 165 pytest tests and two Playwright tests
  passed; Ruff lint/format and diff whitespace checks passed. Mobile/desktop
  screenshots were inspected. Runtime audit: no known vulnerabilities.
- Docker is unavailable locally; GitHub Linux image build, real container
  smoke, isolated restore and image scan are the next required checks.
- Main has no branch protection (API returned Branch not protected, 404).
  No repository settings were changed. Require a reviewed, green PR manually.
- Actual NAS/DSM/ACL/TLS/hardware/backup validation and all real-data operations
  remain unperformed and unauthorized. No secrets or real music/member data
  belong in handoff files, CI or artifacts.

## Continuation

Finish actual CI, correct failures, record the concrete verified source and
checks, and merge the reviewed PR under the standing Git authorization.
Propose the exact prerelease tag/publication milestone once the candidate is
concrete and reviewable; no automatic NAS deployment. After publication,
record its real registry digest, pull evidence and install bundle URL.
