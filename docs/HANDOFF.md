# Agent handoff — latest preview snapshot

This snapshot supersedes the old WP-03 transfer record. Repository files/Git
remain authoritative; inspect the complete comparison on takeover (AGENTS.md).

## Git checkpoint

- Date: 2026-11-20; agent: Codex.
- Current branch: `codex/first-deployable-preview`.
- Comparison base:
  `5e6bacc816f69999bbe88eae11536cc2dee71da2` (PR #7 merged into main).
- Verified implementation head: `4aa216506f1fd4a37dfa3a35de519ed40e25ec34`.
- Intended transfer ref: `origin/codex/first-deployable-preview`.
- Implementation is pushed and fully CI-verified; PR #8 is open at this
  documentation checkpoint, with its merge authorized after final green CI.
  Verify Git/PR history for the later documentation commit and merge; do not
  assume the recorded code head includes this snapshot or is the final main SHA.
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
Web is internal-only; the bounded fixed-destination TCP gateway has no private
mounts and alone publishes loopback. The image uses pinned Python 3.12.16 /
Alpine 3.24 plus the exact Kerberos security patch. It is not published.

## Actual checks and open gates

- Local Windows / Python 3.12.14: 170 pytest tests and two Playwright tests
  passed; Ruff lint/format and diff whitespace checks passed. Mobile/desktop
  screenshots were inspected. Runtime audit: no known vulnerabilities.
- Docker is unavailable locally. Full Linux CI `44797427059` passed on the
  recorded implementation head: 170 tests, two browser tests, Ruff, lock/audit,
  actual amd64 build, Compose default/tools/Debug validation, real container
  mount/startup/auth/mode/persistence/isolated-restore smoke, Trivy vulnerability
  and secret scan, uploaded CycloneDX SBOM/image metadata. Zero HIGH/CRITICAL
  OS/Python findings; no secret findings. Earlier CI failures and their actual
  fixes remain in PROGRESS.md; no scan/test was disabled.
- Full branch diff reviewed; PR #8 had no reviews or unresolved review threads
  at this checkpoint. Nine packages software-verified, 62 unfinished. WP-06/07
  and WP-47a/48/49 retain full worker/archive/NAS gates; WP-10 needs publication.
- Main has no branch protection (API returned Branch not protected, 404).
  No repository settings were changed. Require a reviewed, green PR manually.
- Actual NAS/DSM/ACL/TLS/hardware/backup validation and all real-data operations
  remain unperformed and unauthorized. No secrets or real music/member data
  belong in handoff files, CI or artifacts.

## Continuation

Verify the final documentation CI and PR #8 merge under the standing Git
authorization. Request the distinct release milestone: `v0.1.0-preview.1` on
the verified main merge, followed by the existing GHCR workflow. No release tag
or publication is yet authorized/executed. After approval, publish, verify the
actual pulled digest/attestations/install bundle, and record evidence. That
completes WP-10 (10 complete, 61 unfinished). No automatic NAS deployment.
