# Standard checks and deterministic CI waiting

Reference for the exact commands, timing defaults, exit codes, and diagnostics
used by the workflow in [PROCESS.md](PROCESS.md). The waiter is
`scripts/wait_for_ci.py`: read-only, deterministic, no LLM dependency, and bound
to an exact commit SHA. It never merges, modifies, reruns, cancels, or otherwise
changes GitHub resources.

## Running the waiter

Run through `uv` so the interpreter is pinned and no system Python is required:

```sh
# Pull request checks, bound to the exact pushed head commit.
uv run python scripts/wait_for_ci.py --mode pr --pr 42 --sha "$(git rev-parse HEAD)"

# A specific Actions run (post-merge main CI, release pipeline), bound to its SHA.
uv run python scripts/wait_for_ci.py --mode run --run-id 123456789 --sha <EXPECTED_SHA>
```

`--repo owner/name` defaults to the `origin` git remote. The waiter writes one
compact JSON line to stdout and a result file under the git-ignored
`.dev/ci-wait/` directory (e.g. `.dev/ci-wait/pr-42.json`), so a backgrounded
invocation can be re-read after it exits without polling. Override with
`--result-file`; suppress the file with `--no-result-file`.

On a failed run, retrieve only the failed job/step (see
[PROCESS.md](PROCESS.md), *Efficient failure diagnostics*); do not download all
logs and do not re-download the same logs.

## Defaults

| Parameter | Flag | Default |
| --- | --- | --- |
| Initial wait after push/trigger | `--initial-delay` | 90 s (30 s is enough to make a run discoverable; the waiter also treats 404 as pending) |
| Normal polling interval | `--interval` | 60 s |
| Long-running polling interval | `--long-interval` | 120 s (used after `--long-after`) |
| Switch to long interval | `--long-after` | 600 s elapsed |
| Maximum wait duration | `--max-duration` | 1800 s (30 min) |
| Transient network failures | `--transient-retries` | 3, exponential backoff from `--interval` |
| Required checks (mode=pr) | `--required` | `Foundation (ruff + pytest)` |

The waiter handles all delays internally. One waiting period is one invocation;
never split it into repeated short LLM-driven polls.

## Tool timeout and background waiting

The shell tool timeout must exceed the wait. If the available tool cannot
execute a sufficiently long blocking operation, run the waiter as a supported
deterministic background process, which writes its terminal state to the result
file; do not replace the limitation with repeated short LLM polling. Verify the
process finished before reading the result. If no reliable wait mechanism exists
at all, checkpoint and stop instead of polling manually.

## Exit codes

| Code | Result | Meaning |
| --- | --- | --- |
| 0 | `success` | All required checks succeeded on the exact bound SHA |
| 1 | `failed` | A required/observed check failed |
| 2 | `cancelled` | The run/check was cancelled |
| 3 | `timeout` | Max duration reached; not terminal — **not a success** |
| 4 | `rate_limited` | GitHub rate limit prevented completion within the budget — **not a success** |
| 5 | `unavailable` | API/network unavailable after bounded retries — **not a success** |
| 6 | `mismatch` | SHA mismatch or a required check is missing/skipped — insufficient verification |
| 64 | usage | Argument/repo resolution error |

Only `success` on the exact bound SHA is an acceptable verification. Missing,
skipped, incomplete, stale, or foreign-SHA checks are never success.

## Rate-limit handling

GitHub REST rate limits (403/429 with `X-RateLimit-*`/`Retry-After`) are handled
deterministically inside the waiter: honor `Retry-After` (HTTP-date or seconds)
and `X-RateLimit-Reset`, wait until the permitted retry time, stop with a clear
`rate_limited` checkpoint if that exceeds the wait budget, and make no extra
requests to probe whether a limit reset. Do not treat these as interchangeable
with GitHub GraphQL/secondary limits, LLM provider request or token limits, or
tool execution timeouts. For LLM provider rate limits: stop unnecessary model
interaction, do not retry the same request, preserve the checkpoint, resume when
available, and never claim a fixed delay guarantees recovery.

## Local standard checks

Run the relevant subset before pushing; a full package uses all of them:

```sh
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv run python manage.py check --settings tests.settings
uv run python manage.py makemigrations --check --dry-run --settings tests.settings
uv run pytest browser/   # browser acceptance, separate invocation
```

CI then repeats the Foundation checks plus the full container, security, and
synthetic-acceptance scope unless the change is classified docs-only by
`scripts/ci_changes.py` (only `docs/PROGRESS.md` and `tests/TRACEABILITY.md`
qualify). Do not weaken or skip a required check to save time.

## Compact success evidence

Report: run id, run URL, verified commit SHA, workflow/check name, final
conclusion, and a relevant test summary only when necessary. Do not reproduce
large unchanged logs or code in reports.
