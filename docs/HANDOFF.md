# Agent handoff — latest snapshot

Update this file when the owner says **handoff / Übergabe**. On **takeover / Übernahme**, verify every statement against Git, source and checks. Procedures are defined in `AGENTS.md`; long-term work-package history belongs in `docs/PROGRESS.md`.

## Git checkpoint

- Date (UTC): 2026-11-20 ~11:45 UTC (observed at handoff)
- Outgoing agent: OpenCode
- Branch / upstream: `feature/wp-03-auth-session` / `origin/feature/wp-03-auth-session`
- Comparison base (full SHA): `89c4777d80df0c511190339271f3445961450308` (merge commit of PR #2, tip of `main`)
- Code head (full SHA, CI-verified): `8734c93908dc3ce4fda8916a3684de9f4a984899`
- Handoff docs commits: `6b551e9839bcd168dc38bdf5bb79ce41923a717f` (this snapshot, first version) and the final snapshot commit whose SHA is reported after push (a commit cannot contain its own SHA).
- Intended transfer ref: `origin/feature/wp-03-auth-session`
- Working tree: clean (no staged, unstaged or untracked files)
- PR / merge status: https://github.com/tostman1/notenarchiv/pull/3 — **open, CI green**, **not yet merged**.

## Work status

- Work package / status: WP-03 — **implemented, CI verified, pending merge**. WP-01 and WP-02 are merged into `main`.
- Completed changes since comparison base (3 commits):
  - `650665d` docs: add cross-agent handoff procedure and scoped commit format (AGENTS.md update + this HANDOFF.md template)
  - `e3e8632` feat(accounts): add authentication and session baseline (full WP-03 scope)
  - `8734c93` fix(tests): sort test settings import block (CI lint regression fix)
- Unfinished work / known defects:
  - WP-03 is complete code-wise; only the merge into `main` remains (owner decision).
  - CI job logs are not downloadable with the current GitHub credential scope ("Must have admin rights"); CI status was verified via the runs/jobs API, not log content.
  - `gh` CLI token on the OpenCode machine is invalid; PR/merge API calls use the stored Git credential (`git credential fill`) and the temp credential file is deleted immediately after each call.
  - Real-browser acceptance (Playwright) for login is WP-03a scope; current browser evidence is Django test client + a manual live runserver check (curl) recorded in PROGRESS.md.
  - NAS/hardware validation (V-01) and printer (V-03) remain outstanding per DECISIONS.md; nothing in this handoff claims they were performed.
- Decisions pending from owner: merge PR #3 into `main`; approval to start WP-03a (application shell and navigation).

## Verification

- Local checks (run at handoff, Windows, uv 0.12.5, CPython 3.12.13):
  - `uv run ruff check .` — pass, 0 findings
  - `uv run ruff format --check .` — pass, 47 files
  - `uv run pytest -q` — 78 passed (~3.5s)
  - `uv run python manage.py check` — 0 issues (WP-03 time)
  - Live runserver (curl, real socket): `/healthz` 200 public; `/` 302 → `/login/?next=/`; `/login/` 200 with CSRF token; bad Host header 400
- GitHub CI: run 44736049991 on `8734c93` — **success**; run 44737425748 on
  `6b551e9` (handoff docs) — **success**; earlier run 44733254176 on `e3e8632`
  failed at Ruff lint (fixed by `8734c93`)
- NAS / hardware checks: not run

## Continuation

- Next concrete action: merge PR #3 into `main` (owner approval), then start WP-03a — early application shell and navigation (German base template exists already as part of WP-03; WP-03a adds the full UI-02 navigation set, empty states, accessibility, local-asset offline check, i18n mechanism and the initial Playwright smoke).
- Transfer status: **ready after verified push** — `origin/feature/wp-03-auth-session` is pushed and CI green on every head since `8734c93` (runs 44736049991 and 44737425748 success); final head SHA is reported after the final snapshot commit.
