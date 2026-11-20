# Progress record

Concise status per work package (IMPLEMENTATION_PLAN.md section 6). All work
packages were **Planned** at specification revision 2.0; statuses below
reflect actual completed work only.

| WP | Scope | Status | Commit / PR | Test evidence | Blockers | Next |
| --- | --- | --- | --- | --- | --- | --- |
| WP-01 | Repository, development tooling and minimal CI | Verified | PR #1 merged (merge commit `bcdf272`) | Local checks (below) + GitHub Actions run 44694745130, job "Foundation (ruff + pytest)" success | None | WP-02 |
| WP-02 | Django skeleton and configuration | Verified | PR #2 merged (run 44724272495 success) | Local checks (below) + GitHub Actions run 44724272495, job "Foundation (ruff + pytest)" success | None | WP-03 |
| WP-03 | Authentication and session baseline | Merged, audited | PR #3, merge `245c258` | PR head `7cca167`, CI run 44738003509 passed; auth follow-ups merged with WP-03a | None | Complete |
| WP-03a | Application shell and navigation | Merged, CI verified | PR #4; merge `e913d706d869de14f2e063eb0fb8b2835d548e98` | 90 tests, Ruff lint/format, local Playwright and combined CI run 44747734412 passed | None | Complete |
| WP-04a | Technical logging and mode contract | Merged, CI verified | PR #5; merge `d4b2d2bcfdee21de0628a2141f995b0d49fd3441` | Windows unittest: 5 passed; Linux CI runs 44746685234 and 44747068821 passed | NAS acceptance outstanding | WP-04b |
| WP-04b | Authenticated debug UI | Merged, CI verified | PR #6; merge `ec705b29bc56d212cad1c34369cc5ba9dd9821c5` | 110 local tests, 2 Playwright tests; Linux CI run 44749299835 passed | NAS acceptance pending | WP-05a |
| WP-05a | Durable queue, claim and singleton worker | Implemented, locally verified | `codex/wp-05a-durable-queue`, base `ec705b2` | 141 pytest tests, 2 Playwright tests, Ruff lint/format, lockfile and Django checks passed; details below | Linux CI and NAS acceptance pending | Commit, push and stop as requested; WP-05b remains planned |

## WP-01 — Repository, development tooling and minimal CI

**Delivered** (branch `feature/wp-01-project-foundation`, from `main` at the
v2.0 spec baseline):

- `pyproject.toml` — Python `>=3.12,<3.13`; runtime dep `Django==5.2.10`;
  dev group `pytest==8.4.1`, `ruff==0.14.5`; Ruff target py312, line length
  120; pytest `testpaths = ["tests"]`.
- `uv.lock` — resolved with uv 0.12.5 against CPython 3.12.13 (12 packages).
- `tests/test_foundation.py` + `tests/smoke_settings.py` — interpreter
  baseline, Django 5.2 pin, isolated `django.setup()` smoke (DEBUG=False
  invariant), and the OP-04 `DEBUG_MODE` parse contract.
- `tests/conftest.py` — synthetic-fixture policy fixture (GR-14).
- `.gitignore`, `.dockerignore` — caches, venv, secrets, `.env`, local DB /
  logs / scratch / thumbnails, local `opencode.json`.
- `.github/workflows/ci.yml` — push to `main` + pull_request;
  `permissions: contents: read`; actions pinned to commit SHAs
  (`actions/checkout@v4` = `11d5960a...`, `astral-sh/setup-uv@v5` =
  `d4b2f3b6...`); steps: `uv lock --check`, `uv sync --locked`,
  `uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest`.
- `docs/LICENSES.md` — dependency license inventory mechanism; direct
  licenses verified from installed package metadata (Django BSD-3-Clause,
  pytest MIT, ruff MIT). No project LICENSE file created (owner decision
  pending, D-10).

**Actual local results** (Windows dev machine, uv 0.12.5, CPython 3.12.13):

| Check | Result |
| --- | --- |
| `uv lock` | ok, 12 packages resolved |
| `uv lock --check` | pass |
| `uv sync --locked` | pass, 11 packages installed |
| `uv run ruff check .` | pass (0 findings) |
| `uv run ruff format --check .` | pass (3 files) |
| `uv run pytest` | 8 passed |
| CI workflow YAML | parsed OK (local check; GitHub run not yet observed) |

**GitHub status:** branch pushed (`bf0b826` + `e8e7a95`), pull request #1
opened (`gh` CLI token on the dev machine is invalid; PR created via the
GitHub API with the stored Git credential). GitHub Actions CI on the PR
**passed**: run `44694745130`, job "Foundation (ruff + pytest)" success.
PR #1 merged into `main` (merge commit `bcdf272`) after CI success,
owner-approved.

**Notes:**

- No application code, app packages, or speculative features were created.
- `opencode.json` (local agent config) is git-ignored, not committed.
- Spec docs v2.0 were committed as `docs: commit specification revision 2.0
  baseline` on `feature/project-setup` and fast-forward merged to `main`
  before this work package started (owner-approved).

## WP-02 — Django skeleton and configuration

**Delivered** (branch `feature/wp-02-django-skeleton`, from `main`):

- `manage.py`, `config/` package: `settings.py` (DEBUG always False,
  security defaults, static/WhiteNoise, i18n de, domain roots, processing
  limits, logging baseline), `urls.py` (public `/healthz`), `wsgi.py`,
  `db.py` (SQLite foreign-keys + busy-timeout pragmas via
  `connection_created`), `env.py` (single source for environment parsing;
  full ARCHITECTURE.md §9.1 contract, typed and validated).
- Profiles: `nas` = deployment default (explicit env contract, secret from
  protected file, no auto-creation); `local` = explicitly selected dev
  profile (loopback-only bind enforced, synthetic roots under `.dev/`,
  dev secret generated 0600, roots auto-created). No production security
  setting is weakened by the local profile.
- App boundaries `apps/{accounts,catalog,members,archive,projects,exports,
  printing,jobs}` (registered, empty), `core/` (pure-processing boundary),
  `config/management/commands/validate_config.py` (moved to
  `apps/jobs/management/commands/` — Django discovers commands in installed
  apps; `--service web|worker` writability checks, RAW never probed).
- `.env.example` (no real secrets), `scripts/dev_env.{sh,ps1}`,
  `static/` + `staticfiles/` placeholders, README dev section updated.
- Tests (51): parser contract (profile default/invalid, DEBUG_MODE
  absent/TRUE/FALSE/mixed-case/whitespace/empty/invalid, secret file
  missing/empty/read, hosts required, loopback-only local bind, duplicate
  local roots, int/bool validation, architecture defaults), session
  settings (app boundaries, DEBUG=False, DB path, static/i18n), HTTP
  (healthz public 200 + loopback host, sanitized 500 without traceback,
  bad Host rejected 400), SQLite pragmas (foreign_keys ON, busy_timeout
  5000), `validate_config` subprocess tests (web/worker happy path,
  nas missing config fails loudly, DEBUG_MODE=TRUE still reports Django
  DEBUG False).
- Dependencies added and locked: whitenoise 6.12.0 (MIT),
  pytest-django 4.14.0 (BSD-3-Clause); `uv.lock` updated;
  `docs/LICENSES.md` verified from installed metadata.

**Actual local results** (Windows, uv 0.12.5, CPython 3.12.13):

| Check | Result |
| --- | --- |
| `uv lock --check` | pass (14 packages) |
| `uv sync --locked` | pass |
| `uv run ruff check .` | pass, 0 findings |
| `uv run ruff format --check .` | pass, 38 files |
| `uv run pytest` | 51 passed |
| `manage.py migrate` (local profile) | pass (auth/contenttypes/sessions) |
| `manage.py check` | 0 issues |
| `manage.py validate_config --service worker` (local) | pass, all roots writable |
| Live `runserver` 127.0.0.1:8765 | `/healthz` 200 `{"status": "ok"}`; bad Host header 400 |
| CI workflow | run 44724272495 success (job "Foundation (ruff + pytest)") |

**Notes / deviations:**

- Management commands are discovered from installed apps, so
  `validate_config` lives in `apps/jobs` (operations app), not `config/`.
- Tests run through `tests.settings` (re-exports `config.settings` after
  preparing a deterministic local test environment) because
  pytest-django imports settings before any conftest executes;
  `pyproject.toml` sets `DJANGO_SETTINGS_MODULE = "tests.settings"`.
- `Django OPTIONS` does not accept `foreign_keys` on the 5.2 SQLite
  backend; the pragma is enforced in `config/db.py` instead (tested).
- CI: run 44724272495 on the merged head passed (recorded in the table
  above).

## WP-03 — Authentication and session baseline

**Delivered** (branch `feature/wp-03-auth-session`, from `main`):

- `apps/accounts`: `models.LoginAttempt` (persistent rate-limit records,
  pruned after 24h) + migration 0001; `services.py` (login throttling:
  10 failures per (username, IP) in 15 min, case-insensitive username,
  per-pair, success clears history); `forms.py` (German labels/errors);
  `views.py` (login/logout/home; client IP from first X-Forwarded-For or
  REMOTE_ADDR; open-redirect guard via `url_has_allowed_host_and_scheme`);
  `management/commands/create_archivist.py` (interactive/random-password
  provisioning, no --password argument, username validation, password
  policy enforced).
- `config/settings.py`: explicit `AUTH_PASSWORD_VALIDATORS`
  (similarity/min-8/common/numeric); secure-cookie + SSL-redirect flags now
  derived from the new `env.secure_transport_required` (True in nas, False
  in local loopback) — a data-transport property of the profile, never a
  runtime toggle; `LOGIN_URL`.
- `tests/test_auth.py` (16 tests): unauthenticated root redirected to
  login with `next`, authenticated root available, healthz stays public,
  German login page; valid/invalid login (German error, session state);
  password stored PBKDF2-hashed; relative `next` honored, external `next`
  dropped (open redirect); logout; CSRF enforced on login and logout
  (403 without token, token round-trip succeeds); rate limiting
  (throttle after 10 failures even with correct password, success clears,
  old attempts ignored, per username+IP, case-insensitive); cookie
  contract (local flags off, nas env `secure_transport_required` True,
  always-on HTTPOnly/nosniff/DENY/LOGIN_URL/host validation).
- `tests/test_create_archivist.py` (6 tests): random-password creation with
  hashed storage and one-time display, duplicate rejection,
  set-password requires existing account, invalid username and weak
  password rejected (no account written).
- Test speed: `tests/settings.py` uses a low-iteration PBKDF2 hasher
  (dotted path, test module only) so the suite runs in ~3.5s; production
  settings keep Django defaults.

**Actual local results** (Windows, uv 0.12.5, CPython 3.12.13):

| Check | Result |
| --- | --- |
| `uv run ruff check .` | pass, 0 findings |
| `uv run ruff format --check .` | pass, 47 files |
| `uv run pytest` | 78 passed in 3.39s |
| `manage.py makemigrations --check` | no changes detected |
| `manage.py check` | 0 issues |
| Live runserver (real socket, curl) | `/healthz` 200 public; `/` 302 -> `/login/?next=/`; `/login/` 200 with CSRF token; bad Host header 400 |
| CI workflow | run 44736049991 on `8734c93` success (earlier run 44733254176 on `e3e8632` failed at Ruff lint; fixed by `8734c93`) |

**Notes / deviations:**

- Migrations are excluded from Ruff lint/format (`extend-exclude =
  ["*/migrations/*"]`) because Django's generated serializer does not
  follow the project style; this is standard Django practice.
- "Authorized browser login works" acceptance point is exercised through
  Django's test client (full middleware stack) here; a real browser smoke
  is the stated acceptance of WP-03a (Playwright), which will build on
  this baseline.
- No Playwright yet: browser tests arrive with WP-03a per the plan.
- CI run 44733254176 (head `e3e8632`) failed at the Ruff lint step: an
  unsorted import block in `tests/settings.py` introduced together with the
  test-only fast hasher. Fixed by `8734c93`
  (`fix(tests): sort test settings import block`); CI run 44736049991 on
  `8734c93` passed (job "Foundation (ruff + pytest)" success).

## WP-03a — Application shell and navigation

- UI-02/UI-03: German, translatable navigation, current page and visibly grouped
  unavailable modules. The home view explains availability for review, projects
  and jobs. Debug / Logs appears as a placeholder only in diagnostics mode.
  Keyboard skip link, visible focus, labelled inputs and login/logout feedback.
- Django collects the local stylesheet under its public static URL. No runtime
  asset dependencies. The browser test blocks external requests while retaining
  loopback access and checks applied CSS, keyboard navigation, failed and
  successful login, reload, disabled modules and logout.
- WP-03 follow-up: logout requires POST; throttling uses the direct peer and
  avoids validating credentials during lockout. Behind a proxy, attempts for
  the same username through that proxy share one limit.
- Follow-up audit (2026-11-20): confirmed PR #3 head and merge against GitHub,
  including successful CI run `44738003509`. Pushed the previously local
  browser database fix `400c44dc93fb6b953ee8c0fc45f4690b0ac6482a` to PR #4.
  Restored locked development dependencies locally: Ruff lint/format and
  82 unit tests passed on that head. Integrated current main without
  discarding either work package's progress record. Combined checks and
  browser acceptance are recorded after execution; NAS acceptance is open.
- After main integration: 90 unit tests, Ruff lint/format and the Playwright
  smoke passed locally. The browser test needed execution outside the network
  sandbox to reach its loopback-only synthetic Django test server. PR CI
  previously could not run on the conflicting branch; the progress-record
  conflict is resolved by preserving both packages' evidence.
- Final PR #4 head `557c1f517c14ca51458b6e1ddb73e4159c39a3df` passed
  GitHub Actions run `44747734412`, including the browser smoke. Merged as
  `e913d706d869de14f2e063eb0fb8b2835d548e98`; local main updated by fast-forward.

## WP-04a - Technical logging and mode contract

- Status: implemented locally on the WP-03 main baseline. OP-04 and GR-13
  use the shared mode parser and fixed web/worker roles. Both sinks encode
  allowlisted structured fields. Debug adds bounded, process-locked rotation.
- Five Python 3.12 unittest cases passed on Windows with synthetic logs,
  including restart persistence, retention, concurrent writer rejection,
  sanitized stdout/files and failure with an unusable output directory.
  Direct configuration probes passed for roles, paths and invalid settings.
- Python compilation and whitespace checks passed. The repository pytest
  suite and Ruff could not run locally because these packages are absent.
- GitHub Actions run `44746685234` on implementation commit
  `4ad1a389cb76f4c566835e24a281122fa6443572` passed on Linux: locked
  dependency sync, Ruff lint/format and the full pytest suite (including
  diagnostic tests and the Linux lock implementation). NAS acceptance
  remains outstanding.
- Owner authorization on 2026-11-20: merge PR #5 after successful checks;
  routine Git milestones within agreed scope no longer require repeated
  approval when checks/CI pass and no unresolved findings remain. Recorded
  in AGENTS.md and DEC-08. Documentation-only follow-up is included in PR #5.

## WP-04b — Authenticated debug UI

- OP-04: authenticated Debug-only page, JSON and download routes; Deploy
  rejects access even with historical files. Mode badge and usable navigation
  replace the former Debug placeholder. All responses disable caching.
- Fixed web/worker source IDs, validated job/level/component/time filters,
  source-bound signed cursors, rotation tracking and explicit lost-history
  reset. No arbitrary file path parameter or file mutation.
- Reader limits: 64 KiB / 100 records per page, 1 MiB / 1000 per download,
  4096-byte record fragments. Polling is sequential every two seconds,
  can be stopped, and retains at most 200 DOM rows. Files are re-sanitized;
  malformed, oversized, partial and non-regular/symlink inputs are handled.
- Local Windows / Python 3.12.14: Ruff lint/format, 110 pytest tests and
  2 Playwright tests passed. Browser coverage includes Debug auth/filters,
  live append, sanitized download, logout and offline local assets, plus
  the Deploy shell and direct-route denial. Synthetic data only.
- German archivist guide added. CI and NAS acceptance remain pending at
  this commit; no real association data or NAS operation was used.
- Final implementation head `e9df607b39d1f80409abf98e3b5d77717dd9b0a6`
  passed GitHub Actions `44749299835`, including both browser tests. PR #6
  merged as `ec705b29bc56d212cad1c34369cc5ba9dd9821c5`.

## WP-05a — Durable queue, claim and singleton worker

- OP-02: Job model and migration, payload version/size/domain validation,
  QUEUED/RUNNING/terminal transitions, progress, timestamps, cancellation
  intent and sanitized error codes. A migration seeds the unique worker lease.
- Atomic conditional ORM UPDATEs use short SQLite write transactions before
  reading candidates; no reliance on select_for_update. A partial unique
  RUNNING index and global lease prevent concurrent heavy claims. Worker
  generations and attempt numbers fence progress and completion.
- Lease expiry uses SQL execution time, not a timestamp captured before
  waiting for a write lock. An actual locked-connection expiry regression
  test verifies that a waiting claimant cannot revive an expired worker.
- Stable OS process lock beside the DB remains held even after lease expiry.
  Independent idle/busy heartbeat, 30-second leases, five-second renewal,
  freshness health command and bounded polling. SIGINT/SIGTERM stop new claims.
- Domain processors are deliberately installed by their own packages; only
  registered/validated payloads can enter the queue. No synthetic production
  jobs. No automatic retry or takeover of unfinished RUNNING jobs. Recovery,
  cancellation and fenced publication remain WP-05b; uncertain PRINT failures
  are REVIEW_REQUIRED and cannot re-enter the queue automatically.
- Integration uncovered that a Debug healthcheck would otherwise contend
  with the running worker's rotating log. Entry-point context now gives
  auxiliary management commands sanitized stdout only, preserving the shared
  mode and all security settings. The worker/web keep their file-writer rules.
- Synthetic acceptance: 30/30 competing Django-ORM claims over independent
  file-backed SQLite connections had exactly one winning worker/job. Also
  exercised duplicate same-lease claims, stale attempt/generation/expiry,
  idle/busy heartbeats, real worker CLI process-lock ownership, payload
  rejection, sanitized handler errors and PRINT uncertainty without retry.
- Final local checks (Windows, Python 3.12.14): `pytest -q` — 141 passed;
  Playwright browser suite — 2 passed; Ruff lint/format — passed (67 files);
  offline locked-dependency verification, Django system check, migration drift
  check and whitespace check — passed. Applied the migration and ran the real
  worker command against synthetic local storage. A separate real Debug worker
  and healthcheck coexist successfully without log-file writer contention.
- Owner requested completion, commit, push and then stop on 2026-11-20.
  Do not begin WP-05b or merge this branch without continuation. Linux CI
  and NAS/hardware acceptance are not claimed by local results.
