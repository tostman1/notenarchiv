# Central assignment and edition resolver (WP-32)

`resolution_services.ResolutionSession` loads one consistent SQLite read snapshot
of selected active project positions/participants, saved defaults, personal overrides,
roles/mappings, edition preferences and replacement rules. It is request-local, not
a persistent mutable cache. Inputs/contexts have explicit bounded counts; callers
may narrow the selected rows/participants. Foreign/removed/inactive cells are denied.

The pure `resolve` method selects without DB writes, queries or file I/O. It reuses
the WP-34 mapping and WP-35 replacement scope components plus the same pure edition
choice component used by WP-23a. `verified_resolution`/`resolve_cell` are the public
byte-verifying boundary: check existing safe read/publication/hash validation once
per selected file within the request, then recheck its exact current confirmed
assignments/revision to reject withdrawal during verification. No automatic repair
or fallback on failure.
Future matrix and preflight use this same engine; generation must additionally pin
and revalidate the returned exact inputs at its own snapshot/publication boundary.

Priority and explicit failure contract:

1. Personal per-position override wins, even if another default part exists; role
   mapping applies only otherwise. Position mapping wins over project mapping for
   the saved instrument/key/clef variant. Missing/invalid role mapping never silently
   falls back to the member/default. Without role use the **saved** project default,
   never live member master data. Inactive desired parts and revalidation markers fail.
2. Exact personal edition > position edition > project edition > archive preference
   > sole compatible confirmed edition. Several alternatives without preference are
   AMBIGUOUS; invalid/withdrawn/incompatible explicit/preferred input is INVALID,
   never silently another available version. Pure edition choice is shared, not
   repeated in templates. Corrupted/missing selected bytes return CORRUPT, no retry.
3. Only genuinely MISSING desired-part editions permit explicit one-hop replacement,
   position > project > global. Never replace ambiguity, invalid pin/role or corruption.
   Reuse identical edition choice for the target. No second-hop lookup for playable
   music; cycle traversal is only a fail-closed safety check of rule edges. Return
   desired vs effective part and replacement origin even when the target is missing.
4. Reserve returns RESERVE before part/role/edition resolution; no music.

Frozen Resolution carries project/revision, position/participant, desired/effective
part IDs, exact assignment/file/source-version/hash/size/root/path/file revision,
part/edition/replacement provenance, selected override/mapping/rule/preference IDs,
reason codes and warnings. Missing RAW can warn while an unchanged confirmed managed
copy remains usable. Results never mutate prior files/output or infer approval.

Acceptance tests cover the full priority matrix, manual Posaune 2 when 3 exists,
same role on different notation, immutable explicit pin across preference changes,
missing/ambiguity/invalid/corrupt/withdrawn behavior, one-hop/cycle and revalidation,
read-only/no-query pure cells, request-local per-file verification and independent
migration/restart with actual copied synthetic PDF. Existing browser suite and hardened
container resolver smoke remain gates; no matrix UI or preflight/generation is claimed
by this backend package. Private NAS acceptance stays separate.
