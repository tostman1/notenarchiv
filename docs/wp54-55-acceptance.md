# WP-54/55 acceptance evidence

## Scope and delivery boundary

This record consolidates the additive content foundation and collection/edition
work. Historical entries in `PROGRESS.md` describe their original checkpoints;
their earlier "open" statements are not the current implementation inventory.

The existing #75–90 integration backlog is closed. Each merge passed exact Main
Foundation, Container and Windows checks; the final checkpoint was
`afafd3983fe72fa365832a228a69351576d3bb1d` (run 46024076263).
#91 adds complete bounded 125-edition publication; its Main checkpoint
`674a5e19e17644f4c8b01ff4ad463b57f0264db5` passed run 46034210052.
#92 adds explicit shared-page policy; its Main checkpoint
`4ec462c878761398b379347b10e2ccc37934c5fb` passed run 46050512807.
#93 adds the read-only integrity report and has merged at
`8af05815fbb18f830d7b9acad1ca5a2578a6d140`; its exact Main gate is running.
The final gate and this documentation's integration must pass before package
completion is recorded.

## WP-54 evidence

- Stable exact-version source pages and original/effective geometry:
  `test_source_pages.py`, `test_source_page_backfill.py`.
- Immutable regions/logical revisions, explicit ordered occurrences and scoped
  visual confirmation: `test_content_geometry_models.py`,
  `test_content_confirmation.py`, `test_compound_region_acceptance.py`.
- Legacy assignment IDs, hashes, preferences and resolver semantics retained:
  `test_content_contract.py`, `test_project_content_contract.py`,
  `test_content_preferences.py`, existing matrix/preflight regression tests.
- Interrupted committed backfill, deterministic receipts, rollback/rebuild and
  isolated SQLite restore: `test_interrupted_content_backfill.py`,
  `test_content_history_backfill.py`, `test_content_isolated_restore.py`.
- Protected historical project/archive inputs and unchanged replay after edits:
  `test_content_inputs.py`, `test_project_content_pins.py`,
  `test_mixed_project_content_inputs.py`, `test_project_content_publication.py`.
- Read-only sanitized integrity evidence: `check_content_integrity` and
  `test_content_integrity.py`. This reports relational/history consistency;
  publication byte verification remains a separate existing safeguard.

## WP-55 evidence

- Independent collections, typed containment versus related editions, equal-title
  UUID identity and reproducible inheritance/local provenance:
  `test_collections.py`, `test_catalog_corrections.py`.
- Explicit retained correction/withdrawal with stale fences and atomic rollback:
  `test_catalog_correction_views.py`, `browser/test_catalog_correction.py`.
- Complete 125-work, two-instrument region identity/continuation scenarios:
  `test_full_instrumental_booklet.py`; actual 125-edition signed durable-worker
  publication: `test_full_booklet_publication.py`.
- Deutsche Messe parent and separately addressable movements with ordered shared
  continuations across sources: `test_mass_content_sequences.py`.
- One neutral byte-identical BASE, never one CLEAN copy per excerpt:
  `test_compound_publication.py`, `test_compound_publication_command.py`.
- Explicit extracted regions, whole page once or repeated page, with previewed
  signed consequences and retained original occurrence pins:
  `test_content_shared_page_policy.py`. Expansion to a whole page requires its
  independent whole-file musical approval; partial confirmation cannot expand it.
- One shared project selection engine, persisted exclusive edition preferences,
  matrix/preflight agreement, signed authorization and historical worker replay:
  `test_project_content_resolution.py`, `test_project_content_preflight.py`,
  `test_project_content_publication.py`, `browser/test_project_content.py`.

## Recovery, limits and exclusions

Use a schema-compatible backup for rollback. Disabling new use does not authorize
an old-binary downgrade after new-schema writes or reused withdrawn positions.
Retain original PDFs, confirmed metadata and protected historical snapshots.
No real-data migration, cleanup, production provisioning or deployment is implied.

Selections remain bounded to 125 content editions, 16 distinct physical inputs and
100 MiB; parser, scratch, output and worker limits remain active. One heavy worker
is retained. Missing music requires acknowledgement; reserve and occurrence order
are preserved. No automatic approval or uncertain print retry is introduced.

All fixtures are synthetic. POSIX worker and real-browser checks are CI evidence,
not local Windows or physical NAS acceptance. Native Windows writes remain disabled
under DEC-15. Actual RAW ACL/account provisioning and physical power-loss acceptance
are separate. No private archive/member data is sent to CI or external AI.

OCR, compound scan segmentation, new physical-production/template compaction modes,
duplex/cutting/folding expansion and forScore integration are subsequent packages;
they are not claimed here and are not started under this completion assignment.
