# Job recovery, cancellation and publication contract (WP-05b/05c)

The queue is application code, not a deployed domain processor. The published
0.1.0-preview.1 image remains unchanged. No worker/NAS deployment or new image
release is part of this milestone. WP-14 registers the real ARCHIVE_PUBLISH backend;
there are no production demo jobs or arbitrary command/payload submission routes.

## Ownership and restart

`run_worker` holds DATA's canonical `worker.lock` for its entire lifetime.
SQLite lease expiry alone never authorizes recovery. After obtaining that same
OS lock, the successor increments the worker generation, fences the predecessor,
starts an independent heartbeat and inspects interrupted attempts. A fresh DB
lease can outlive a crashed process; the OS lock, not elapsed wall time, proves
that the old publisher no longer owns the boundary.

Each claim creates an immutable-numbered attempt record. Final outcomes remain
in history when the queue row is retried. Handler defaults are one attempt and
no retries. Retrying requires explicit idempotence and a bounded `max_attempts`
(1–5). Only explicit `RetryableFailure`, cooperative shutdown or reconciled
crash recovery can retry; unexpected exceptions fail without blind repetition.
Automatic retries have persisted exponential backoff. PRINT never retries,
regardless of handler policy; uncertain acceptance requires human review.

## Durable external effects

Call `context.publish(key, payload, apply)` only for a short final no-clobber
publication primitive. Stage, hash and inspect outside the transaction. The
key is stable per logical job effect, and its bounded JSON payload cannot change
meaning. Payload/result metadata stays in the local DB, never technical logs.

The service first persists PENDING intent, then validates OS ownership, worker
generation, job attempt, lease and cancellation under a short SQLite write
transaction before invoking `apply`. A successful callback returns bounded JSON;
the lease is checked again before recording APPLIED. Returning to an already
APPLIED key reuses its stored result. Domain code must not perform long copies,
OCR, network submission or arbitrary file writes inside this callback.

WP-14 adds `context.commit_metadata(callback)` for short pure DB updates under
the same current attempt/lease/OS-owner fence. A handler may supply a pure DB
`acknowledge(context, intent)` hook: after recording APPLIED, it commits domain
metadata in the same transaction, also during successor recovery. This includes
recovering an already effected operation whose job was cancelled. It must never
perform filesystem/network effects. Metadata failure leaves the durable intent
pending, rather than claiming a half-acknowledged success.

Only an apply callback that knows no final publication occurred may raise
`NoEffect`; the fenced service records ABANDONED and propagates the failure.
An acknowledgement error cannot make that assertion after an external effect.
Ambiguous I/O errors keep PENDING and require reconciliation. PRINT's explicit
no-retry/uncertain-acceptance rules remain unchanged.

SQLite cannot atomically commit filesystem/network effects. A crash or callback
exception may leave PENDING after an actual external change. A registered
`reconcile(context, intent)` hook must inspect evidence and report APPLIED with
its verified result, ABANDONED when no effect exists, or REVIEW_REQUIRED. Hooks
must not blindly repeat effects. Missing/failed/ambiguous reconciliation requires
review and blocks retries. Concrete archive copy/path rules are documented in
[FILE_PUBLICATION.md](FILE_PUBLICATION.md). Archive ingestion remains a later package.

## Cancellation and child processes

Queued cancellation is an atomic terminal transition. Running cancellation
only records a request; the UI says "Abbruch angefordert" until the processor
and owned children have stopped. Handlers call checkpoints regularly and use
`context.run_process` for subprocesses. Pure Python handlers must cooperate;
an unresponsive handler is not falsely declared cancelled. Stop the worker
process through its service manager if necessary, then use the recovery policy.

The helper uses explicit arguments, no shell, bounded deadlines and discarded
stdout/stderr. POSIX groups receive TERM followed by KILL and live-group checks;
Windows uses a waiting launcher assigned to a non-breakaway Job Object before
the target can spawn. Cleanup waits for zero active processes. An unverified
stop becomes REVIEW_REQUIRED and stops the worker; it cannot become CANCELLED
or automatically retry. This containment is not a security sandbox for arbitrary
untrusted executables. Native PDF limits are implemented in [PDF_CORE.md](PDF_CORE.md).

Cancellation preserves already completed effects. Uncertain PRINT acceptance,
including a cancellation/completion race, always needs review and never claims
that already submitted paper was recalled.

## UI and evidence

Authenticated business routes `/jobs/` and `/jobs/<uuid>/` work in both modes.
Lists paginate 25 rows; detail shows the last 20 attempts, progress, a fixed
German error message and fresh worker availability. Refresh is explicit.
Cancellation is POST-only with CSRF. No job payload, raw exception or log text
is rendered. The ARCHIVE_PUBLISH backend adds no arbitrary submission route;
indexing/review submission UI remains in the corresponding later packages.

Synthetic acceptance includes real worker process death between external effect
and intent acknowledgement, idempotent reconciliation, old-attempt rejection,
bounded retry/backoff, PRINT uncertainty, 20 independent SQLite claim/cancel
races, actual child/grandchild cleanup, and a real browser-to-worker cancellation.
NAS filesystem/hardware acceptance is separately tracked, not inferred from CI.


## Development worker commands and fixed bounds

After migrations, set `NOTENARCHIV_SERVICE=worker` and run
`uv run python manage.py run_worker` in the explicit local/synthetic profile.
`--once` checks the queue once; otherwise polling continues. Use
`uv run python manage.py worker_healthcheck` to check the independent heartbeat
and unexpired lease. The current installation Compose files deliberately deploy
no domain worker. No dummy handler is registered to make these commands appear
productive.

Leases last 30 seconds and heartbeat every five seconds, including idle periods.
Expiry is checked against database time at the SQL statement, so waiting for a
SQLite write lock cannot revive expired ownership. Payloads need a registered
domain validator, schema version 1 and at most 16 KiB JSON. Singleton lease,
unique RUNNING constraint, atomic claims and generation/attempt fencing coexist
with the lifetime OS lock. SIGINT/SIGTERM stop new claims and invoke cooperative
shutdown/recovery policy above. Auxiliary commands preserve DEBUG_MODE and
Django DEBUG=False without competing for a rotating writer slot. This current
contract consolidates the earlier README worker baseline.
