# Progress record

Concise status per work package (IMPLEMENTATION_PLAN.md section 6). All work
packages were **Planned** at specification revision 2.0; statuses below
reflect actual completed work only.

| WP | Scope | Status | Commit / PR | Test evidence | Blockers | Next |
| --- | --- | --- | --- | --- | --- | --- |
| WP-01 | Repository, development tooling and minimal CI | Verified | PR #1 merged (merge commit `bcdf272`) | Local checks (below) + GitHub Actions run 44694745130, job "Foundation (ruff + pytest)" success | None | WP-02 |
| WP-02 | Django skeleton and configuration | Verified | PR #2 merged (run 44724272495 success) | Local checks (below) + GitHub Actions run 44724272495, job "Foundation (ruff + pytest)" success | None | WP-03 |
| WP-03 | Authentication and session baseline | Implemented, CI green | PR #3 open (run 44736049991 success, head `8734c93`) | Local checks (below) + GitHub Actions run 44736049991 success (earlier run 44733254176 failed at Ruff lint; fixed by `8734c93`) | None | Merge PR #3, then WP-03a |

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
