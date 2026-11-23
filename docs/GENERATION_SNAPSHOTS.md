# Immutable generation authorization (WP-36b)

Generation authorization is a server-only service exposed through authenticated,
CSRF-protected preflight POST. No PDF renderer, export download or enabled generation
button is shipped by WP-36b; premature worker execution fails explicitly.

The signed 30-minute preflight token binds actor, project, report fingerprint and
an independent request UUID. `authorize` rebuilds the report with the central
resolver and bounded byte/parser verification outside a write transaction. It then
acquires SQLite's writer via a conditional no-op project-revision update, reloads
the resolver dependency graph and compares its canonical payload before creating
snapshot, relational pins, job and run in one transaction. No file I/O occurs under
that writer lock. All full folders require every active shared position, reserves
included. Participant subsets do not create personal piece lists.

Dependencies include selected project graph, catalog/instrument/role values,
overrides/mappings/replacement rules/preferences, all compatible confirmed editions,
source versions/presence, publication operation/intent/proposal evidence and pending/
unavailable archive records. This deliberately conservative fingerprint may require
a fresh preflight after some unrelated metadata changes within the selected scope.

Replaying the same valid request UUID returns the original run, not another job.
Changed/stale/forged preflight or incomplete/foreign/duplicate missing decisions are
rejected. An intentionally fresh token can authorize another historical run.
Failures during pin/enqueue/run creation roll back the complete authorization.

`GenerationSnapshot`, `GenerationRun`, `SnapshotParticipant`, `SnapshotPosition`
and `SnapshotInput` preserve canonical payload, exact part/edition/hash/version,
saved display names, positions/numbering/reserves and acknowledged placeholders.
References use PROTECT. ORM update/delete operations on these history models are
denied. SQLite update triggers additionally reject changes to snapshot/run/pin
records and content identity/review changes on pinned archive files/assignments/
source versions. A follow-up migration restores triggers after SQLite table remake.
Future schema changes must preserve/reinstall these guards. Direct administrative
SQL deletion is not an application API and remains subject to maintenance/backup
policy; no destructive retention is implemented.

Pinned files cannot be withdrawn through the archive service. Unexpected filesystem
changes still cannot be prevented at the DB layer: worker loading verifies exact
pin inventory, file identity/revision/state, assignment and actual managed bytes.
It uses only the snapshot and never calls the current project resolver. File hashes
are checked once per physical input, with cancellation/lease checkpoints between
pins. Any changed/missing/corrupt/withdrawn source fails closed. Project/default/list
edits do not rewrite existing payloads or pins.

Until WP-37b, the registered GENERATE handler validates authorization then fails
with no output. Generic queue history/cancellation/restart behavior is retained;
it does not claim artifact recovery that cannot yet exist. WP-37b must add durable
publication/idempotent artifact reconciliation, without weakening this input gate.

Tests: `test_generation_snapshots.py`, independent-process
`test_generation_snapshot_persistence.py` (SQLite reopen/concurrent replay), and
`browser/test_generation_authorization.py`. Synthetic data only. No NAS filesystem,
production load, deployment or real musical quality acceptance is claimed.
