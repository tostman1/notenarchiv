# Progress record

Concise status per work package (IMPLEMENTATION_PLAN.md section 6). All work
packages were **Planned** at specification revision 2.0; statuses below
reflect actual completed work only.

| WP | Scope | Status | Commit / PR | Test evidence | Blockers | Next |
| --- | --- | --- | --- | --- | --- | --- |
| WP-01 | Repository, development tooling and minimal CI | Verified | PR #1 merged (merge commit `bcdf272`) | Local checks (below) + GitHub Actions run 44694745130, job "Foundation (ruff + pytest)" success | None | WP-02 |
| WP-02 | Django skeleton and configuration | Implemented (local) | pending PR | See notes below | CI run pending on PR | WP-03 |

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
| CI workflow | pending on PR (not yet run) |

**Notes / deviations:**

- Management commands are discovered from installed apps, so
  `validate_config` lives in `apps/jobs` (operations app), not `config/`.
- Tests run through `tests.settings` (re-exports `config.settings` after
  preparing a deterministic local test environment) because
  pytest-django imports settings before any conftest executes;
  `pyproject.toml` sets `DJANGO_SETTINGS_MODULE = "tests.settings"`.
- `Django OPTIONS` does not accept `foreign_keys` on the 5.2 SQLite
  backend; the pragma is enforced in `config/db.py` instead (tested).
- CI has not run yet (branch unpushed); results to be recorded here when
  the PR checks are observed.
