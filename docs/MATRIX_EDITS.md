# Direct matrix cell and saved default editing (WP-33b)

Cells expose controlled combined part/notation/exact-version dropdowns built only
from central resolver session eligible hash-verified archive assignments. Each
selection is an actor-bound 15-minute signed receipt of assignment, exact part,
arrangement, file revision and SHA-256. No raw filename/path, arbitrary PDF or free
text assignment is accepted. Reserve cells have no editor. More than 200 alternatives
per arrangement fails explicitly instead of truncating or guessing a version.
Alternative integrity reads are additionally bounded to 512 MiB and 60 seconds
per visible window; budget exhaustion is actionable, not silently truncated.

`matrix_edit_services.set_cell` validates actual bytes outside the short SQLite
transaction, then obtains the existing project revision write barrier and rechecks
the active same-project position/participant, exact arrangement and confirmed
assignment/file revision. Saving pins desired part and edition together in the
existing PartOverride, retains scope UUID and records append-only MatrixChange
protected old/new parts and editions. Invalid, withdrawn, corrupt, stale or foreign
selections roll back atomically. Explicit re-selection clears needs_revalidation;
there is no automatic inheritance/reset in this package. Batch/reset follows WP-33c.

Column headers edit the saved participant project default through the existing
WP-31 service. Master members, other people, positions/numbering, roles and all
personal per-position overrides remain unchanged. Cell/default persistence and
display both use the central WP-32 resolver, no second selection logic in templates.

Local hash-pinned HTMX 2.0.11 (maintained release, 0BSD) updates the bounded matrix
panel including fresh project revision and labels after a mutation. Reloading the
entire visible window intentionally re-resolves affected default-dependent cells,
not unrelated stored data. It refreshes every form's optimistic revision together.
Same-origin requests, CSRF hidden fields, authenticated endpoints, eval/script
execution disabled, no history caching or CDN. One in-flight panel edit at a time;
errors and stale revisions are shown in German without silent retry. Ordinary POST
forms retain redirect/conflict behavior when JavaScript is unavailable. Pagination
values are normalized server-side; client parameters cannot change stored scope.

Acceptance uses deterministic actual copied PDFs, manual part 2 when 3 exists,
exact alternative notation/version, actor/expiry/freedom/confirmation/hash/SQLite
fences, unchanged other cells/defaults/common list, history rollback, requests with
and without HTMX, default preserving overrides, independent process race/reopen
and real browser successful edits plus conflicting second tab. Existing reserve
test now checks forms within reserve rows; new editors elsewhere are approved
scope, not weakening reserve protection. No NAS, deployment or generated artifacts.
