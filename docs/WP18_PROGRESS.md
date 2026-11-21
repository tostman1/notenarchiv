# WP-18 independent progress record

Branch: `feature/wp-18-secure-preview`.
Comparison base: `5874c7c49f39ef05b3c8599819861fa6c27d8bac`.
Status: implemented and locally verified; PR/Linux/container verification pending.

Owner approved independent WP-18 implementation, tests, commits, push and PR,
but explicitly reserved merge approval. WP-19 remains a parallel independent
package. Existing shared PROGRESS/HANDOFF snapshots are deliberately unchanged.

Dependencies WP-17, WP-13 and WP-03a were verified from repository history and
recorded successful CI. Base main CI `44897447951` succeeded. The isolated
worktree was safely relocated with `git worktree move` to permanent local
storage; no other worktree/branch was switched or modified.

Implemented own preview service/views/URL namespace, immutable safe file reads,
local PDF.js canvas viewer, navigation/zoom, bounded native thumbnails and tests.
No models, indexing, recognition, Python dependency/lockfile or shared transfer
records were changed. Root URL registration is a small isolated integration.
See PDF_PREVIEW.md for API, security, limits and traceability.

Local results: 406 tests passed / 39 platform/permission skips; all five browser
tests passed, including the new real PDF.js offline/navigation/zoom test.
Ruff lint/format passed. POSIX gates remain mandatory in Linux CI. Direct
management checks without a selected profile correctly refused missing NAS
secrets; synthetic-settings system check and migration-drift check then passed.
Final targeted suite after busy-lock/forged-receipt and vendored integrity
coverage: 22 passed / one POSIX skip. Complete diff reviewed; upstream notices
and binary assets preserve exact bytes through scoped Git attributes.
PR CI is not claimed complete at this checkpoint. NAS/real-data validation,
release and deployment remain unperformed.
