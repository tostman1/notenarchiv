# Preflight inspection (WP-36a)

Authenticated project preflight inspects an explicit selection of active participants
and shared positions. Selection is read-only; it is not a personal piece list or a
full-folder export. Future full output must include the whole shared list.

`build_report` captures project and resolver inputs in one short SQLite read
transaction and reuses `ResolutionSession.verified_resolution`. Musical assignments
are therefore identical to matrix results for the same selected graph. Reserves
have no music. Part/edition provenance and exact confirmed file/hash remain visible.

Missing music requires an explicit checkbox per requested participant/position.
Ambiguous, invalid, incompatible, changed, corrupt and unreadable selections are
blocking failures and cannot be acknowledged as harmless missing music. Known
confirmed files marked missing/corrupt block the corresponding unresolved desired
part. Pending/rejected candidates are arrangement-level notices, never usable notes.
Corrections link to existing matrix/rule/ensemble workflows.

Selected usable PDFs are checked once per physical file through the existing safe
read-only hash snapshot and isolated resource-limited PDF processor. Layout warnings
show native A3, landscape, rotation, crop/UserUnit, custom and mixed paper formats.
Original pages are unchanged. No pairing or print renderer is provided by this WP.
MARCHBOOK printing remains explicitly unavailable.

Bounds: 5,000 cells, 128 distinct inspected files, 512 MiB cumulative input, 60 s
report deadline and at most 30 s per structural parser. Files are processed serially;
the shared nonblocking preview parser lock prevents concurrent native inspection.
Temporary private staging is removed on normal completion/failure. Resource limits
produce actionable failures, not implicit approval. Heterogeneous large NAS load
acceptance remains separate. A small synthetic success is not a production SLA.

Acknowledgement tokens bind the exact report fingerprint to project and actor and
expire after 30 minutes. POST recomputes and verifies all selected inputs; changed
report or incomplete/foreign acknowledgement is rejected. This is **inspection-only**:
no durable authorization, relational pins, generation jobs or exports exist yet.
WP-36b must atomically bind authorization/snapshot/enqueue and recheck dependencies;
this acknowledgement endpoint is not an alternate enqueue API.

Coverage: `tests/test_preflight.py` and `browser/test_preflight.py`; deterministic
synthetic inputs only. Auth/CSRF, no mutations, missing/ambiguity/reserve parity,
stale/forged tokens, corruption/parser failures, unavailable inputs, conflict notices,
per-file reuse and native A3/rotation/custom geometry are exercised.
