# Managed local development and CI maintenance

Windows: `uv sync --locked`, then `./dev.ps1 start`. Python equivalent:
`uv run python scripts/dev.py start`. The foreground launcher migrates/collects
assets and opens `http://127.0.0.1:8085/` through a launcher capability login.
Use `./dev.ps1 status`, `stop` or `restart` in another terminal. Enter `kill` in
the foreground terminal, then answer `yes` to `Stop the development server?
(yes/no)`. `no` leaves it running. Ctrl+C also shuts down. Use `-ManualAuth` /
`--manual-auth` to test ordinary login and `-NoBrowser` / `--no-browser` to avoid
opening the browser. No autoreload child is created; restart after source edits.

The launcher uses one fixed ignored `.dev/launcher` profile/database and generates
an unpredictable per-start capability. Only the local profile, literal loopback
host/peer and capability can enter the fixed `synthetic-local-developer` account.
It has an unusable password; no arbitrary user identifier is accepted. NAS profile
rejects configuration; DEBUG_MODE does not enable it. CSRF/manual authentication,
session middleware, permissions, host validation and Django DEBUG=False remain.

Lifecycle control authenticates a loopback endpoint with a random secret/identity;
the PID is informational only. Stale files do not authorize process termination.
A stable process lock prevents simultaneous launchers. Port conflicts fail without
killing the listener. Local state stays ignored. Production startup is unchanged.

Authentication investigation: normal password/form/session/redirect/throttle tests
passed; no reproduced account-login defect is established. The old sourced helper
permits ambient DATABASE_PATH/profile overrides, so account creation and server
can use different DBs. The launcher removes those overrides and isolates synthetic
accounts. Do not assume a reported password failure is fixed by auto-login; use
manual mode and verify DB, host (localhost vs 127.0.0.1), cookies and throttle.

Static diagnosis: local DEBUG=False runserver does not supply Django's debug static
handler; WhiteNoise needs collected assets or local finders. The launcher collects
assets and local profile enables WhiteNoise finders. Favicon is explicitly linked
to a bundled SVG. Structured errors identify named endpoints or static/unmatched
categories, never raw business paths, query tokens or request bodies. The standard
Django runserver production-use warning is not an application failure; the launcher
does not use runserver or change production hosting.

CI baseline: main run 45179603788 took 10:00 wall time, Foundation 7:00, Container
2:53; uv setup+sync ~3 s, Docker build 17 s, scanner verification 1 s, scan 12 s.
Final documentation-head run 45177706547 took 11:23 (Foundation 8:50, Container
2:27) despite unchanged code. Unit/browser execution dominates.

Maintenance runs Foundation and Container concurrently (Container only waits for
classification), cancels obsolete runs only within the same PR, preserves main/
workflow-call verification and existing check names. Only PROGRESS.md and
TRACEABILITY.md-only PRs may omit the container; deployment/security docs, unknown
files and mixed changes fail closed to full verification. Foundation remains full
even for those docs. Main and release reusable workflows always build/scan/test.
uv uses lock-keyed cache, BuildKit local cache is lock/Dockerfile-keyed, cached Trivy
archive is hash-verified every run; vulnerability database is refreshed normally.
No mandatory code PR check is removed. Main protection API reports 404/unprotected;
manual reviewed-green gating remains. Actual after timings await PR CI.

Agent workflow: prepare implementation and acceptance docs before final-head CI;
report final CI/merge SHA in PR/chat and record integration in the next approved
package, rather than triggering another expensive docs-only full run solely to
store the previous run ID. Never reuse old green CI after code changes.

WP-37b is paused and locally preserved at `837b2013b8b2f218955bdbf19c8d53444baced5d`
on `feature/wp-37b-personal-folders` (not pushed). After maintenance integration,
verify clean status, `git switch feature/wp-37b-personal-folders`, review checkpoint
and safely merge updated main, resolving conflicts without discarding partial work.
