# Agent handoff — verified catalog/member integration checkpoint

Date: 2026-11-21. Git/source and repository specifications remain authoritative.

## Current scope and authorization

Finish the active WP-11/12 first, then WP-17, then the separate simplified
Synology installation milestone. The owner's 2026-11-21 extension supersedes the
old stop after WP-17. After installation integration, reassess a manageable,
dependency-ready manual archive slice that can be completed and verified.
Do not assume every suggested archive/OCR WP is due in one session.

Each milestone requires full acceptance, reviewed diff, commit/push/separate PR,
green CI, authorized merge and verification of main before advancing. Routine
Git is authorized. Additional releases, NAS changes, real archive/member data,
destructive production work, paid services and fundamental architecture/security
changes still require separate approval. Record/defer them; continue independent
safe software work where appropriate. Published preview artifacts stay immutable.

## Actual Git checkpoint

- Current follow-up branch: fix/job-browser-sqlite (from verified main).
- Catalog/member branch: feature/wp-11-12-catalog-members, merged PR #12.
- Current follow-up base: a2d7264e43c823c612236e29effc414c8879cd97 (verified main).
- Full catalog/member comparison base: 470e7c8b0421d91ae38fbc65b888c16e70b1088c.
- Reviewed source head: 3f1b30969843f508ffda082c4f80d94155aff392, pushed on
  the catalog/member branch; PR #12. Full CI 44841036938 passed. This documentation
  checkpoint preceded merge a2d7264e43c823c612236e29effc414c8879cd97; final
  PR CI 44841417182 and main CI 44841705128 passed. Trees match. A subsequent
  local Windows browser run found a shared-memory SQLite test lock failure;
  the current bounded fix switches browser tests to isolated file SQLite.
  Verify its local/browser/CI integration before WP-17.
- WP-05b/05c is complete and merged through PR #11 at 470e7c8.
  Reviewed head: 74e7312acc87e3b0d4a5d1302d592c47b188ce3b.
  Final PR CI 44823906492 and main CI 44824237705 passed; merged tree matched.
  Do not duplicate that framework. Earlier full A comparison: 0be8e44..470e7c8.
- Requested B branch/worktrees were checked before creation; none existed.
  The current checkout is reused. Keep existing branches and already integrated
  clean .dev/wp03a / .dev/wp04a clones. No branch deletion was requested.

## WP-11/12 implementation and evidence

Implemented catalog UUID models and protected relationships: works, arrangements,
instrument/notation variants, playable parts, aliases, expected parts and reusable
instrumentation templates. Members have one required regular part. Equal human
names/titles never merge; variants/part codes have normalized canonical uniqueness.
Aliases target a real variant or part; ambiguity is retained, not auto-resolved.

Complete authenticated German CRUD/search/detail/pagination, typed reference
choices, active/inactive status, confirmed unused-record deletion, protected
references and optimistic stale-edit detection are implemented. Referenced musical
identity cannot be silently reinterpreted. Template application is a bounded,
atomic independent copy with explicit replacement confirmation. Unknown and known
empty expectation lists differ. No archive availability/role/processor is invented.
See CATALOG.md and stammdaten.de.md.

Local Windows gates passed: 265 full pytest tests, four Playwright tests, Ruff
lint/format, system/migration-drift checks and whitespace. Tests include actual
migrate/reopen persistence in independent interpreters, normalized duplicates,
controlled assignment, active-member protection, stale forms, copy independence,
empty/unknown/bounded expectations, CSRF/XSS/search and a real German browser flow.
Desktop/mobile screenshots were inspected. Full Linux CI 44841036938 passed:
265 tests, four browser checks, actual amd64 image/Compose/container/restore and
vulnerability/secret checks. No submitted reviews or unresolved threads. The
complete diff was reviewed; final documentation CI and merged-main verification
remain required.

## Published baseline and counts

The immutable 0.1.0-preview.1 image is unchanged. Its application/tag source is
62d85b36189293a59df2ef39729a538f5c53ad3b; RELEASES.md records the exact digest,
successful completion run 44817372155, signatures and assets. New source features
are not claimed to be available in that image. No new release is authorized.
Software-verified count: 14 WPs, 57 unfinished (56 required plus optional WP-43).
WP-11/12 has passed local/Linux/container acceptance; verify its authorized merge
and main CI before starting the next milestone.
Main protection was unavailable (actual API 404); retain the manual reviewed-green
PR gate. Actual NAS/DSM/ACL/TLS/resource/backup tests remain unperformed and
unauthorized. Synthetic data only; never include secrets or real music/member data.

## Next actions

Complete and integrate the browser file-SQLite follow-up, then start
feature/wp-17-pdf-foundation from latest verified main. Then implement
feature/synology-simple-install: standalone configuration.yaml using the published
immutable digest, minimal essential edits, safe first-install preparation and
primary concise German guide. Preserve advanced Compose and technical runbooks;
validate actual container behavior and future bundle inclusion. No release-asset
rewrite or live NAS action. Afterwards reassess the next manual archive slice.
