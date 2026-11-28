# Development process

This is the canonical, repository-wide workflow for every development session,
agent, epic and work package. It replaces earlier scattered instructions. Where
this file and [standard-checks.md](standard-checks.md) conflict with older
paragraphs in other documents, this file wins for process; requirement IDs and
the invariants in [../AGENTS.md](../AGENTS.md) always win for scope and safety.

## Binding principle: waiting is not reasoning

An LLM must not repeatedly reason, generate commentary, invoke tools, or
reconstruct context solely to wait for an external operation to finish. External
waiting includes GitHub Actions execution, pull request checks, mergeability,
branch protection, post-merge CI, artifact generation, and GitHub API rate-limit
recovery. One CI phase is one deterministic waiting operation and one final
result, not a sequence of recurring agent interactions.

This is enforced, not advisory: do not poll GitHub in an LLM-driven loop, do not
repeat `gh run view` / `gh pr checks` / `gh pr status` while checks are pending,
do not insert a short sleep between repeated model turns, and do not re-fetch
unchanged status or re-download CI logs while a run is in flight. Waiting must
become deterministic automation, not agent reasoning. These restrictions do not
weaken any CI, review, security, integration, or verification requirement.

## Canonical sequence

Owner refinement (2026-11-28, DEC-17) separates development commits from delivery
boundaries. Accumulate related implementation, tests, fixes and documentation on
one feature/integration branch, typically three to six related increments, not a
rigid quota or a mandatory PR per WP. Choose size by complexity, dependencies,
risk and cumulative reviewability. Security-critical and migration-sensitive work
may justify smaller batches or earlier full verification.

Within a batch, run targeted local tests and relevant lint, formatting, migration
and consistency checks; review and commit focused Conventional Commits as durable
checkpoints, then continue development. Do not automatically run full regression
or Actions after every commit, test, documentation edit or review correction.
At the integration boundary, run combined local verification once, independently
review the cumulative diff against the verified Main baseline, and obtain full
exact-head PR CI followed by exact post-merge Main CI. Intermediate commits and
superseded candidates need not each have independent full CI evidence.

Remote checkpoints: current CI triggers are Main pushes, pull-request events and
reusable workflow calls. A push to a feature branch with **no open PR** does not
start CI; use that existing mechanism when a remote checkpoint is needed. Once a
PR exists, pushing another head starts verification, including draft PRs. Do not
use skip-CI markers, disable checks or change permissions to avoid gates. Recheck
triggers/protection if this mechanism changes. No force-push or history discard
is authorized. A checkpoint without CI is not successful integration evidence.

Prefer existing deterministic tools for recurring mechanical work. Add bounded,
cross-platform, testable scripts with compact machine-readable evidence when
their recurring benefit warrants maintenance. Use repository-scoped skills when
structured guidance is needed. Preserve human or agent judgment for product
decisions and code review. Avoid trivial wrappers and orchestration frameworks.
Process improvements accompany functional delivery. Working product behavior
and practical usability take priority. These rules preserve all acceptance,
privacy, security, review and integration gates.

1. Assemble a cohesive batch within the approved scope, using targeted checks,
   incremental review and focused local commits between integration boundaries.
2. Run the combined required local verification once at the integration boundary
   (see [standard-checks.md](standard-checks.md)); review the cumulative diff.
3. Commit with a small English Conventional Commit; write the message to
   `.agent-commit-message.txt` and use `git commit -F` per [AGENTS.md](../AGENTS.md).
4. Push the verified commit to a feature branch and open the pull request.
5. Identify the GitHub Actions run or the PR checks for that exact head commit.
6. Invoke the deterministic waiter once, bound to the exact commit SHA and the
   required checks (commands in [standard-checks.md](standard-checks.md)).
7. Let the deterministic operation wait without model-driven polling. Continue
   independent work on a separate branch/worktree where safe; never modify the
   frozen candidate merely to add unrelated work. A changed head needs new CI.
8. Read the compact terminal result.
9. On success, continue to the next authorized integration action.
10. On failure, retrieve only the relevant failed job/step information.
11. Diagnose and fix the actual cause.
12. Re-verify only after a changed commit, a failed check, or another meaningful
    state change. Never reuse stale, unrelated, skipped, or insufficient checks
    as successful verification.

Apply the same efficient waiting to final-head CI and post-merge main CI. A
timeout, an expired wait, or an assumed outcome is never a successful CI result.
Never merge on an assumption.

## Required verification gates (preserve, do not weaken)

- Exact-commit verification: the green evidence must correspond to the exact
  intended HEAD SHA.
- Required CI checks per the contract in
  [standard-checks.md](standard-checks.md), including docs-only classification.
- Branch protection / reviewed-green-head gating (main is currently unprotected;
  the gate is manual and remains mandatory).
- Pull request review and unresolved-findings resolution before merge.
- Migration, security, and regression checks.
- Release traceability and deployment authorization remain separate, explicit
  gates. This process changes the cost of waiting and orchestration only.

## Efficient failure diagnostics

On CI failure: fetch the failed job and failed step first; prefer failed-step
logs over full workflow logs; avoid downloading unrelated successful job logs;
do not repeatedly download the same logs; store large logs locally and inspect
only the relevant sections; escalate to complete logs only when targeted
diagnostics are insufficient. Do not truncate information needed for reliable
root-cause analysis. On success, report only the evidence: run id, run URL,
verified commit SHA, workflow/check name, final conclusion, and a relevant test
summary only when necessary.

## Token efficiency

Read the relevant files rather than rescanning the whole repository; reuse
verified information from the current session; refresh state only after a
meaningful change; prefer targeted searches over large dumps; keep tool output
concise; batch independent read-only checks; avoid redundant `git status`/`diff`/
branch/remote queries; do not restate the full implementation after every minor
step; do not reproduce large unchanged code in progress reports. Persist durable
knowledge in the authoritative documents and reuse requirement IDs, work package
IDs, and decision records rather than reproducing their full contents. Use
deterministic scripts for repetitive mechanical work; reserve LLM reasoning for
analysis, implementation, design decisions, debugging, and meaningful review.
Token efficiency never reduces implementation quality, safety, test coverage, or
accurate reporting.

## Checkpoint and recovery

When work is interrupted by a rate limit, external dependency, tool timeout, or
session loss, preserve a concise checkpoint sufficient to resume without redoing
verified work. Record: active work package; branch; commit SHA; implementation
status; PR number and URL; Actions run id and URL; completed and pending
verification; current blocker; exact next action; and whether a merge or
deployment already occurred. On resume, verify only the external state that may
have changed. Do not restart the whole work package or repeat already-verified
steps without a concrete reason. Store the checkpoint outside Git; do not grow a
set of redundant status documents. Use [PROGRESS.md](PROGRESS.md) for work-package
history and [HANDOFF.md](HANDOFF.md) for the latest transfer snapshot.

## Reports

Keep progress reports concise: actual changes, checks, results, and remaining
issues. Do not invent measured token or API savings; where no measurement exists,
label any comparison as illustrative.
