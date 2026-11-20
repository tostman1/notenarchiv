# Agent handoff — autonomous milestone session

Date: 2026-11-20. Repository files and Git remain authoritative.

## Scope and stopping point

The owner authorized three complete, separate integrations in this order:

1. WP-05b/05c: feature/wp-05b-05c-job-management.
2. WP-11/12: feature/wp-11-12-catalog-members.
3. WP-17: feature/wp-17-pdf-foundation.

Start each from latest verified main. Require complete acceptance, reviewed
full diff, green CI, merge and verified merged result before advancing. Stop
after WP-17. No WP-13, extra archive/OCR work, new release or NAS deployment.
Routine commit/push/PR/merge authorization remains active under AGENTS.md.

## Current Git checkpoint

- Active implementation branch: feature/wp-05b-05c-job-management.
- Full comparison base: 0be8e44b4333d74fc38be8fdbe424c80d13c4612 (main).
- Main integration CI 44819635852 passed. Original checkout was clean.
- All three requested branches/worktrees were checked before starting; none
  existed. The current checkout is reused. Preserve existing branches and the
  clean, already integrated .dev/wp03a / .dev/wp04a clones.
- This snapshot accompanies the first implementation commit; verify actual
  commit/upstream and complete staged/unstaged diff before takeover. Linux CI
  and PR/merge evidence must be added after they actually run.

## WP-05b/05c implementation and local evidence

Canonical OS publisher ownership, predecessor fencing/recovery, bounded explicit
idempotent retry/backoff, attempt history, durable operation intents and domain
reconciliation hooks are implemented. Unresolved external effects require review.
Concrete archive copy/path operations remain WP-14, not silently implemented here.

Running cancellation stays a request until processor/owned children stop. POSIX
process groups and a Windows Job Object launcher provide actual descendant
cleanup. Unverified stop and uncertain PRINT acceptance require review; PRINT
never automatically retries. German business job list/detail, bounded paging,
progress/history, refresh, worker freshness and CSRF-protected cancellation work
in both modes. No payload/raw exception is exposed or production demo job added.
See JOB_FRAMEWORK.md and auftraege.de.md.

Local Windows checks passed: 218 pytest tests, 3 Playwright tests, Ruff lint and
format, Django system check, migration drift and diff whitespace. Acceptance
includes real worker process death between external effect and acknowledgement,
recovery without duplicate effect, old-attempt rejection, bounded retry/backoff,
20 independent SQLite claim/cancel races, child/grandchild termination and actual
browser cancellation of a running subprocess. Linux/container CI remains the
next integration gate; never infer its success from local results.

## Published baseline and remaining gates

The unchanged 0.1.0-preview.1 image is already published and verified; application
source/tag is 62d85b36189293a59df2ef39729a538f5c53ad3b. Exact digest, successful
completion 44817372155 and signatures/assets are recorded in RELEASES.md.
This session changes source, not the published image or NAS installation.
Baseline: 10 software-verified WPs, 61 unfinished; this milestone adds two only
after full verified integration. Main protection is unavailable (actual API 404),
so enforce the manual reviewed-green-PR gate. No repository settings changed.
Actual NAS/DSM/ACL/TLS/hardware tests remain unperformed and unauthorized. No
real music/member data or secrets may enter Git, CI, logs or handoff documents.

## Next action

Finish full diff review and first milestone commit/push/PR. Verify actual Linux
CI; resolve every defect before merge. Confirm main integration before starting
WP-11/12. Preserve the complete acceptance criteria and separate branch/PR
boundaries. Continue through WP-17, then provide the consolidated report and stop.
