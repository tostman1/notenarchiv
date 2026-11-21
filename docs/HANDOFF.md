# Agent handoff — active simplified Synology installation

Date: 2026-11-21. Git/source and specifications remain authoritative.

## Scope and authorization

Complete the current feature/synology-simple-install milestone, then reassess a
bounded dependency-ready manual archive slice. The owner explicitly revoked the
old stop after WP-17 and authorized routine implementation/commit/push/PR/merge
when complete acceptance, reviewed diff and green CI permit. Do not leave partial
branches to chase a later package. Keep one main implementation milestone.

Additional releases, actual NAS/infrastructure changes, real music/member data,
destructive production work, force pushes and architecture/security changes
retain separate approval. Defer those actions. No such action has occurred.
Published v0.1.0-preview.1 tag/image/assets remain immutable and unchanged.

## Actual checkpoint

- Active branch: feature/synology-simple-install, created after root/status,
  branch/worktree checks. Current implementation/docs are uncommitted at this
  snapshot; inspect/preserve all tracked and untracked changes.
- Comparison base: c12e71cc7c3d5676a5be5a4cadee1a39e6ea8cfc, verified main.
- WP-17 is complete via PR #14. Source 309081c77ca296da1bdb8e1b13704da1c5aecc91
  passed CI 44844708708. Final head 27f77f8d390cf76b181fa5805f42c04e5026ddfd
  passed CI 44845116222, merged at the current base; main CI 44845475304 passed.
  Exact merged tree matched. Linux 319 tests, four browsers and actual native
  musl image PDF/container/restore/security acceptance passed. Windows 317 tests
  plus two POSIX-only skips. See PDF_CORE.md and LICENSES.md.
- WP-11/12 was resumed and completed in PR #12 (merge a2d7264), with the
  concurrent file-SQLite browser follow-up PR #13 (merge 2f4b0e9). All source/main
  CI passed and trees matched. WP-05b/05c is complete via PR #11 (470e7c8).
  See PROGRESS.md for full SHAs and CI checkpoints; do not duplicate them.
- Preserve existing branches and integrated clean .dev/wp03a/.dev/wp04a clones.
  Main protection was unavailable (actual API 404); retain reviewed-green PR gate.

## Installation implementation and remaining gates

Standalone configuration.yaml uses the published immutable digest, fixed
/volume1/docker/notenarchiv subdirectories and three mandatory edits: actual
UID:GID, hostname and HTTPS origin. No .env/custom YAML parser/new service.
Read-only RAW/archive web mounts, non-root, protected file secret, private
network/gateway, startup/health, explicit migration and interactive account
provisioning remain intact. No real archive is attached automatically.

prepare-install.sh creates only missing directories/key, checks canonical paths,
existing ownership/modes and actual non-admin account/group membership. Existing
files/secrets/modes are preserved; missing secret beside existing DATA fails.
RAW host checks include ownership/ancestor rename and sticky-parent rules.
No recursive chmod/chown, overwrite, automatic migration/account or app startup.

Primary INSTALL.de.md now follows eight practical steps. README is concise;
advanced installation, update, restore, Debug, developer and worker documents
retain/consolidate technical details. Future release bundling includes the new
YAML/helper/guide and pins their image to release-digest.txt at packaging time;
installers need no preprocessing. Existing release assets are never rewritten.

Final local full pytest: 323 passed, two POSIX-only skips; four browsers passed.
Six focused bundle tests also passed, including source preservation,
reproducibility, no overwrite and digest drift. Ruff (120 files), compilation,
actionlint and Bash syntax passed. No local Docker is installed. New CI tests
actual Compose plus the published and local candidate images' full first-install flows, interactive
hidden-password provisioning, key preservation, host/container RAW denial,
identity/mount/network constraints, migration/restart persistence and preparation
negatives. Those CI tests have not yet run. Inspect every result; do not mark
this milestone verified before them.

## Counts and next action

15 fully software-verified/integrated WPs; 56 unfinished (55 required plus
optional WP-43). Installation is an ops usability slice, not full WP-48/07/22
completion. Actual DS224+/DSM/ACL/TLS/firewall/filesystem/load/backup acceptance
remains private, unperformed and separately authorized. New source features
are not in the published preview image; no additional release is authorized.

Finish final review/local checks, commit/push/open a separate installation PR,
resolve all CI failures, then verify the merged main. After that assess the next
manageable complete manual archive integration boundary against IMPLEMENTATION_PLAN
and DEVELOPMENT_SEQUENCE; do not begin an enormous speculative chain of WPs.
