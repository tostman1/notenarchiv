# Atomic matrix batch edits and explicit reset (WP-33c)

AS-04/AS-08 extend the WP-33b panel with per-person selected-cell controls. A batch
is bounded to 25 distinct active musical positions for exactly one active project
participant.
Batch integrity verification is bounded to 512 MiB of unique inputs and 60 seconds;
repeated exact receipts are verified once per request. Budgets abort, never truncate.
Select the common playable part/notation once in the column header, then explicitly
select a confirmed exact edition for each selected position. Only
selected positions are submitted for mutation. There is no automatic choice of a
sole/preferred/replacement edition, or silent use of an existing manual pin.
Unselected cell controls do not mutate anything. Scope and notation are checked
server-side, not inferred from UI state or position numbers.

`matrix_batch_services.set_cells` verifies every actor-bound WP-33b signed exact
choice before the write transaction. The existing SQLite project revision write
barrier fences project and archive writers, all choices are checked again for
their exact arrangement/part/file revision/hash, then overrides are saved with
protected per-cell MatrixChange history under one project revision. Invalid,
missing, withdrawn, corrupt, foreign, expired, duplicate, mixed-notation or stale
selections abort the entire batch; failures during writes/audit also roll back.
No skipped positions, partial success or automatic retry.

Reset one cell with its explicit button or selected cells with the header reset
button. Reset requires no edition, active arrangement or active desired part: it deactivates only the
selected personal overrides, retaining their identity, desired part, exact edition
and old historical protected references. Reset creates append-only change records
with old pins and null selected pins. A selected cell without an override is a
documented no-op within the guarded request. Re-editing reactivates the same scoped
identity with a new protected history event. Existing data migrates active=True.
Duplication retains active/reset states, not source-project history; list replacement
and review counts consider only effective active overrides.

After reset the single central resolver uses normal role mapping / saved project
default and edition preference precedence. Reset never writes a member default,
changes roles, invents confirmed music or suppresses missing/ambiguous statuses.
Saved default changes preserve all explicit active overrides. Historical reset
pins are never eligible for new output merely because they remain referenced.

HTMX refreshes the bounded visible panel/revisions. German error messages say that
the whole selection remains unchanged; deliberate fresh selections are required
after a conflict. Auth, CSRF, same-origin/no-eval/no-script/history controls and
normal no-JS forms remain active. HTML-associated `form` controls connect selected
cells to exactly one participant's header form; real browser coverage verifies
HTMX includes them. There are no runtime external assets or new processing engine.

Acceptance: deterministic synthetic actual PDFs, manual part 2 while 3 exists,
notation edition, complete invalid-batch and mid-audit rollback, withdrawn/revalidation
reset preserving protection, exact same-person scope, defaults/common list unchanged,
actual concurrent SQLite batch race and independent process reopen, browser multi-save,
single reset, invalid batch, stale tab, reload and JavaScript-disabled selected reset.
Private NAS acceptance is separate.
