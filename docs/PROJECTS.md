# Durable project graph and CRUD (WP-29)

Projects have UUID, non-unique human name, ACTIVE/ARCHIVED state, revision,
regular/marchbook dimensions and cover settings. Authenticated German CRUD,
search/pagination, rename/edit, explicit duplication, archive/reactivate. No hard
project delete or generated outputs at this milestone. Archived projects retain
all records but reject normal edits; reactivation is explicit and revision checked.

Protected models: one shared ProjectPosition list (stable reserve/arrangement IDs),
ProjectParticipant with exclusive member/guest identity and saved default part,
project roles/mappings, part overrides, project/position edition preferences and
project/position replacement rules. Cross-project references are rejected by model
and service validation, plus SQLite uniqueness/check constraints. Ensemble role is
not a playable part; mapping's exact variant must match. New explicit editions
require exact compatible confirmed hash-verified assignment and post-lock revision
recheck. Mapping and rule editors use [ENSEMBLE.md](ENSEMBLE.md) and
[RULES.md](RULES.md); the central resolver uses [RESOLUTION.md](RESOLUTION.md).
Matrix view consumes the same engine ([MATRIX.md](MATRIX.md)); direct/batch editing
remains WP-33b/c.

Project revisions use write-first conditional UPDATE in short atomic SQLite
transactions. Stale requests get a German 409 conflict, not lost updates. Append-only
revision records retain actor/event/time and relevant settings. All future domain
editors use the same project revision service. No personal piece-list model exists.

Duplication obtains an exclusive SQLite write boundary without changing the source
revision, bounds graph size, copies configuration and all associated project records,
creates fresh project/position/participant/role/override/preference IDs and remaps
every local FK. Member/catalog/archive IDs are shared protected immutable references;
guests obtain fresh project-local identities. Historical withdrawn pinned editions
are preserved, never reinterpreted as available new choices. The source graph and
prior outputs remain unchanged. Associated removed rows keep IDs/history; active
position order is unique, inactive slots have no order. Shared list mutation and
numbering use [PIECE_LIST.md](PIECE_LIST.md); participant selection/default refresh
uses [PARTICIPANTS.md](PARTICIPANTS.md).

Local synthetic acceptance covers same-title projects, full graph mapping and clone
isolation, protected records/append-only history, invalid cross-project/edition/
variant/cyclic-rule states, CSRF/auth/escape, stale CRUD/duplicate, real independent
file-SQLite writers and interpreter restart. Browser checks CRUD/duplicate/archive
and simultaneous editor conflict. Container/security/NAS evidence stays explicitly
separate; no real association data or deployment is authorized by software tests.
