# Agent handoff — latest preview snapshot

This snapshot supersedes the old WP-03 transfer record. Repository files/Git
remain authoritative; inspect the complete comparison on takeover (AGENTS.md).

## Git checkpoint

- Date: 2026-11-20; agent: Codex.
- Current documentation branch: `codex/preview-publication-record`; target: main.
- Comparison base:
  `5e6bacc816f69999bbe88eae11536cc2dee71da2` (PR #7 merged into main).
- Released application/tag source: `62d85b36189293a59df2ef39729a538f5c53ad3b`
  (PR #8 merged; final PR/main CI `44798017241` / `44798414658` passed).
- Verified release-pipeline integration/main checkpoint:
  `24c3c8ea175b5c9d39df0813182cdbd39f55075b` (PR #9; PR CI `44816957849`
  and main CI `44817342191` passed).
- Intended transfer ref: `origin/main` after the final documentation PR.
  Verify Git/PR history for the later documentation commit and merge; neither
  source checkpoint includes this snapshot's own future commit.
- Other clones: `.dev/wp03a` and `.dev/wp04a` are clean and their implementations
  are already integrated. Preserve them; no branch/worktree deletion is approved.

## Verified baseline

WP-01/02/03/03a/04a/04b/05a are software-verified and merged. WP-03a's original
Playwright DB-access failure was fixed by `400c44d`, integrated at `557c1f5`,
verified in CI run `44747734412` and merged in PR #4. WP-04a is in PR #5;
WP-04b in PR #6 (CI `44749299835`). WP-05a is in PR #7 (CI `44757097570`).
No worker is deployed by the published first preview. WP-05b remains planned.

## Current authorized work

The owner's latest priority shift authorizes the first empty/synthetic-data
web-only technical preview, not real archive access or a live NAS deployment.
The owner separately approved tag `v0.1.0-preview.1` and GHCR publication;
both are now complete. This authorization does not cover live NAS deployment.
DEC-09 and IMPLEMENTATION_PLAN.md record its scoped dependency/order changes.
WP-09/06/07/08/10 and early WP-47a/48/49 slices are grouped into one coherent
preview branch. Full package gates remain in DEVELOPMENT_SEQUENCE.md.

Implemented: Dockerfile, Compose web/tools, root/mount/secret/identity guards,
explicit migration/provisioning, guarded Gunicorn, honest responsive preview
UI, extended CI/security/SBOM, approved-tag GHCR pipeline and operator runbooks.
Web is internal-only; the bounded fixed-destination TCP gateway has no private
mounts and alone publishes loopback. The image uses pinned Python 3.12.16 /
Alpine 3.24 plus the exact Kerberos security patch. Published image:
`ghcr.io/tostman1/notenarchiv@sha256:e6e01416737702598458af8c9167f2353e09074c445281d640eaa34f10658f4d`.
See RELEASES.md for the actual install bundle, release and attestation URLs.

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
- Original tag run `44815669883` passed all required checks and pushed/pulled
  the image; digest selection then failed before attestations/release creation.
  PR #9 fixed the selection and added constrained recovery with 18 regression/
  trust-boundary cases. No original check was disabled or falsely counted.
- Completion run `44817372155` succeeded using the retained original artifact,
  mandatory archive hash and exact existing-image match. No rebuild, retag or
  image overwrite. Signed origin/promotion and CycloneDX SBOM were published.
  Independent local cryptographic verification bound both claims to the exact
  signer workflow/commit. Signed claims match the downloaded release assets.
- All five asset hashes, all 12 install bundle files, source/version/amd64/
  non-root metadata and anonymous registry digest retrieval were verified.
  Docker remains unavailable locally; actual Docker pulls ran in Actions.
- Ten packages software-verified, 61 unfinished (60 required plus optional
  WP-43). WP-06/07 and WP-47a/48/49 retain full worker/archive/NAS gates.
- Main has no branch protection (API returned Branch not protected, 404).
  No repository settings were changed. Require a reviewed, green PR manually.
- Actual NAS/DSM/ACL/TLS/hardware/backup validation and all real-data operations
  remain unperformed and unauthorized. No secrets or real music/member data
  belong in handoff files, CI or artifacts.

## Continuation

Verify the final publication-record PR/CI and use RELEASES.md / INSTALL.de.md.
The requested preview release is complete. The next deployment milestone is
separately authorized synthetic NAS acceptance (WP-22 slice), with no real
archive attachment. Future independent software lanes and their real
dependencies remain in DEVELOPMENT_SEQUENCE.md. Do not silently begin unrelated
packages or treat release authorization as NAS deployment approval.
