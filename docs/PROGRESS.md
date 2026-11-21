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
| WP-05a | Durable queue, claim and singleton worker | Merged, CI verified | PR #7; merge `5e6bacc816f69999bbe88eae11536cc2dee71da2` | 141 local tests, 2 browser tests; Linux CI 44757097570 passed | NAS acceptance pending | Web-only preview per DEC-09; WP-05b remains planned |
| WP-05b / WP-05c | Recovery, cancellation and job UI | Merged, CI verified | PR #11; merge `470e7c8b0421d91ae38fbc65b888c16e70b1088c` | 218 tests, 3 browser tests; final PR CI 44823906492 and main CI 44824237705 passed | None for software scope | WP-11/12 |
| WP-11 / WP-12 | Musical catalog and members | Merged, CI verified | PR #12, merge `a2d7264`; browser follow-up PR #13, merge `2f4b0e9` | 265 tests, four browsers; final main CI 44842489941 passed | None for software scope | Complete |
| WP-17 | Bounded PDF foundation | Merged, CI verified | PR #14, merge `c12e71c` | 319 Linux tests, four browsers; native image checks; main CI 44845475304 passed | NAS resource acceptance separate | Complete |
| WP-13 | Archive identities and state transitions | Software verified; integration pending | PR #16, source `2c91b43`, base `4805142` | 48 focused tests; full Linux CI 44881080792: 373 tests, four browsers, actual container/install/security checks passed | Final head/main CI gate | Finish before WP-14 |
| WP-09 | Service-aware mount and startup validation | Merged, software verified | PR #8; merge `62d85b3` | 19 storage tests locally; actual Linux container/host negatives in CI 44797427059 passed | Private NAS acceptance remains WP-22 | Retain NAS gate |
| WP-06 / WP-07 | Hardened image / Compose | Preview web/tools slices verified | PR #8 | Actual amd64 build, Compose, non-root/read-only startup, mount/auth/mode/persistence/restore smoke passed in CI 44797427059 | Full worker gate remains WP-05b | Full packages remain partial |
| WP-08 | Extended CI and container verification | Merged, software verified | PR #8; main CI 44798414658 success | Lock/audit, 170 tests, 2 browser tests, actual build/Compose/container/restore, image/secret scan and SBOM passed | Main is not branch-protected (API 404) | Enforce manual reviewed-green-PR gate |
| WP-10 | Versioned container release pipeline | Verified, published | `v0.1.0-preview.1`; PR #9 recovery fix | Original checks/build 44815669883; publication completion 44817372155; pulled digest, signed origin/SBOM and install assets verified (RELEASES.md) | None for preview publication; NAS deployment remains unperformed | Separately authorized synthetic WP-22 |
| WP-47a / WP-48 / WP-49 | Backup / install / rollback | Preview slices implemented; CI restore verified | PR #8 | Install/restore/update/debug guides; actual isolated container restore passed in CI 44797427059 | Full archive/NAS/two-version acceptance remains outstanding | Retain full package gates |

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
- Later owner priority shift on 2026-11-20 explicitly resumed work for the first
  deployable preview. PR #7 head `960201c337ea1e0ae5095938dd7f6e330edcdee3`
  passed full Linux CI `44757097570` and merged as `5e6bacc816f69999bbe88eae11536cc2dee71da2`.

## First deployable technical preview — DEC-09

- Baseline inspection: clean WP-05a branch and clean `.dev/wp03a` / `.dev/wp04a`
  clones; all prior code preserved. WP-03a's browser transaction fix is already
  pushed, CI-verified and merged. No duplicate logging/UI implementation.
- 71 original packages (70 required, one optional). Seven are now fully
  software-verified/merged. Five deployment IDs and three early safety/operator
  slices form the preview path. Full worker/archive/hardware gates are retained;
  see DEVELOPMENT_SEQUENCE.md for the complete register and independent lanes.
- Implemented a web-only container/Compose candidate with protected empty or
  synthetic mounts, loopback-only HTTPS-proxy backend, explicit migration and
  interactive provisioning, persistent SQLite and a maintenance lock. Runtime
  does not auto-migrate or launch unfinished job processors. Placeholder UI is
  responsive, German, visibly unavailable and unable to modify archive data.
- Python image and build-only uv are digest-pinned; runtime Django updated to
  the verified 5.2.19 LTS security patch and Gunicorn 27.0.1 added/locked. Local
  locked runtime audit (pip-audit 2.10.1): no known vulnerabilities. Runtime and
  build/CI dependency notices updated from actual package metadata/license files.
- Local Windows checks at this snapshot: 165 pytest tests, two Playwright tests,
  Ruff lint/format and diff whitespace checks passed. Desktop/mobile screenshots
  visually inspected; no horizontal overflow. No local Docker executable exists;
  actual Linux image build, container smoke and image scan are pending GitHub CI.
- Workflow prepares checked image-artifact publication to GHCR, immutable version
  policy, registry pull/digest verification, signed provenance/SBOM and an install
  bundle/GitHub prerelease. No image availability, release or live NAS deployment
  is claimed before actual evidence. Actual main protection is absent; manual
  reviewed green-PR gate remains in force, without unapproved repository settings.
- Operator runbooks and German quickstart included. Actual DSM version, ACLs,
  certificate/proxy, resources and backup destination still require private
  authorized synthetic NAS acceptance. Real archive/member attachment is forbidden
  in this preview and has not been attempted.
- PR #8 implementation `0c2ff1d9487ae846e8d4826970904f6ad7c656ba`: CI run
  `44792816290` passed all Foundation checks and the actual Linux/amd64 image
  build. Compose validation failed at its model assertion: inactive tool
  services are correctly omitted by default. The follow-up explicitly checks
  both the web-only default and enabled tools profile; no safety/test is removed.
  Container runtime/restore/image scan remain pending this correction.
- Runs `44793166558` / `44793924558` passed Compose but showed no published
  port on the internal-only bridge while the web process was running. Docker's
  default-gateway port publication behavior requires a frontend attachment.
  The implementation preserves web's internal-only network and adds a bounded,
  mount-free TCP gateway from the same image; it has no private storage access
  and only forwards to fixed web:8000. CI now asserts that web has no default
  route and the gateway has no bind mounts; operator commands recreate both.
- CI run `44795938169` on `04c17e4895be6bea7ff806215d768279856e2f2c`
  passed Foundation, amd64 image build, Compose validation and the complete
  real-container/isolated-restore smoke. Trivy blocked publication with 101
  HIGH/CRITICAL findings in Debian 12 OS packages (zero Python-package findings).
  The follow-up uses the official Python 3.12.16 Alpine 3.24 base, pinned by
  registry-verified digest. Both build/runtime use the same musl base; all
  current runtime Python dependencies are pure Python. Future native packages
  must re-verify compatibility. No vulnerability exclusions or weakened scan.
- Startup now rejects known network/FUSE SQLite DATA filesystems before write
  probing; host preflight also rejects non-canonical secret paths.
- Alpine CI `44797068444` also passed build, Compose and complete runtime/restore
  smoke. Its scan found 16 HIGH findings, all in inherited `krb5-libs` 1.22.2-r1;
  Alpine's official 3.24 package index supplies the fixed 1.22.3-r0. The shared
  build/runtime base now installs that exact fixed version. Local checks after
  the storage changes: 170 pytest tests, Ruff (82 files), actionlint and diff
  whitespace checks passed. No scan finding is ignored.
- Final preview source `4aa216506f1fd4a37dfa3a35de519ed40e25ec34` passed
  CI `44797427059`: locked environment, Ruff, 170 Linux pytest tests, two
  Playwright tests, runtime audit, actual amd64 image build, default/tools/Debug
  Compose models, complete synthetic container/isolated-restore smoke, image
  vulnerability/secret scan and uploaded CycloneDX SBOM/image metadata.
  Trivy reported zero HIGH/CRITICAL OS/Python findings and no secrets. The
  full branch diff was reviewed; PR #8 has no submitted reviews or unresolved
  review threads at this checkpoint. Documentation-only follow-up records
  this evidence before the standing-authorized integration. No GHCR publication
  or NAS deployment has occurred. Nine packages are now software-verified;
  62 remain unfinished until WP-10's approved publication (then 10 / 61).

## WP-10 — First approved preview publication

- Owner explicitly approved `v0.1.0-preview.1` and GHCR publication on
  2026-11-20, following the reviewed PR #8 integration. No NAS deployment
  or real-data attachment was approved.
- Release source: `62d85b36189293a59df2ef39729a538f5c53ad3b` on main;
  final PR CI `44798017241` and main CI `44798414658` both passed.
- Annotated tag `v0.1.0-preview.1` was pushed and remotely verified against
  that exact source commit. Release run `44815669883` is the publication
  evidence checkpoint; completion and actual digest are recorded below only
  after registry/release verification.
- Original run `44815669883` passed all checks and pushed/pulled image digest
  `sha256:e6e01416737702598458af8c9167f2353e09074c445281d640eaa34f10658f4d`.
  Publication then stopped because `.RepoDigests[0]` still referred to the
  loaded `notenarchiv-ci` repository. Attestations/install release had not run.
- The correction selects the GHCR digest by repository and fails on absent
  or ambiguous results. Explicit recovery validates the original approved tag
  source, original workflow and all required successful check jobs; downloads
  the retained candidate with mandatory archive SHA-256 validation; and requires
  the existing registry version to match the candidate. It cannot rebuild,
  create a missing version, move a tag or overwrite a different image.
  Recovery signs a factual original-build/promotion predicate and the original
  SBOM; it does not mislabel the recovery commit as the application's build source.
  Local regression/policy checks: 27 tests passed, Ruff and actionlint passed.
- PR #9 source `6e3ce21e4230116d36557e0d44a2571e8ca5e43b` passed complete
  CI `44816957849` and merged at `24c3c8ea175b5c9d39df0813182cdbd39f55075b`;
  main CI `44817342191` also passed. Original tag and image stayed unchanged.
- Recovery run `44817372155` succeeded, including mandatory original artifact
  archive hash, equality with the existing GHCR image, authenticated image pull,
  signed original-build/promotion predicate, signed CycloneDX SBOM and GitHub
  prerelease/install assets. The exact reference is
  `ghcr.io/tostman1/notenarchiv@sha256:e6e01416737702598458af8c9167f2353e09074c445281d640eaa34f10658f4d`.
- Independent checks: anonymous registry manifest returned the same digest;
  all five downloaded release asset hashes matched GitHub metadata; all 12
  installation bundle files matched the original tag or digest file. Linux/
  amd64, non-root, version and source image metadata verified. `gh attestation
  verify` cryptographically verified both predicate types with the exact signer
  workflow/commit; their signed origin/SBOM claims match the release files.
- WP-10 is complete for this preview. Current count: 71 total, 10 software
  packages verified, 61 unfinished (60 required plus optional WP-43). Full
  worker/archive/operations gates remain; no NAS or real-data action occurred.
  See RELEASES.md for immutable digest, release/install URLs and evidence.

## Owner-authorized autonomous sequence — 2026-11-20

Three separate, sequential integration milestones: WP-05b/05c on
`feature/wp-05b-05c-job-management`, WP-11/12 on
`feature/wp-11-12-catalog-members`, then WP-17 on
`feature/wp-17-pdf-foundation`. Each starts from latest verified main after the
predecessor's complete acceptance, reviewed diff, green PR CI and verified
merge. Commit/push/PR/merge are authorized under the standing rules. Stop
after those three; no WP-13, archive/OCR expansion, release or NAS deployment.

### WP-05b / WP-05c local implementation

- Canonical OS-lock ownership authorizes successor recovery and worker-generation
  fencing, even when a dead predecessor's DB lease is still fresh. Old attempts
  cannot update state or enter the publication interface. Attempt history and
  delayed bounded retry policy persist in SQLite. PRINT never retries.
- Durable generic operation intents and domain reconciliation hooks surround
  short fenced final-publication callbacks. PENDING uncertainty requires evidence;
  unresolved effects block retries. No archive model/copy implementation is added.
- Cooperative cancellation, TERM/KILL POSIX groups and race-free Windows Job
  Objects stop owned descendants before terminal cancellation. Unverified cleanup
  requires review and stops the worker. PRINT cancellation/acceptance races remain
  REVIEW_REQUIRED without re-submission.
- Authenticated German paginated list/detail, progress, attempt history, explicit
  refresh, worker availability and CSRF-protected POST cancellation. No arbitrary
  submission, demo processors, raw payloads or exception text. Debug mode is not
  required. The published 0.1.0-preview.1 image is unchanged.
- Acceptance: actual worker process death between file effect and DB acknowledgement,
  reconciliation without duplicate publication, stale attempts, retry/backoff,
  PRINT uncertainty, 20 independent SQLite claim/cancel races, actual owned child/
  grandchild termination, and real browser cancellation of a running child process.
- Local Windows checks: 218 pytest tests, 3 browser tests; Ruff lint/format, Django
  system check, migration-drift check and diff whitespace checks passed. Actual
  Linux container CI and integration status are recorded in the subsequent checkpoint.
- Source `77d4f60d92c828ba407a89a180437e46ad72c0eb`, PR #11: full Linux
  CI `44823399459` passed Foundation, all browser checks, actual amd64 image
  build, Compose validation, real container/restore and vulnerability/secret scan.
  Full diff reviewed; no submitted PR reviews/unresolved threads at this checkpoint.
  Documentation-only follow-up records verified acceptance before integration.
  Current software-verified total: 12 WPs, 59 unfinished. No new image release.

## Owner extension and resumed milestone — 2026-11-21

The owner explicitly extended the session: finish the actual active WP-11/12
branch without discarding existing work; complete WP-17; then implement separate
`feature/synology-simple-install` with standalone `configuration.yaml` and a
concise primary German installation guide. Afterwards reassess and deliver the
next manageable dependency-ready manual archive slice when fully verifiable.
The earlier stop after WP-17 is revoked. Ordinary Git integration is authorized;
additional releases, NAS changes, real data and destructive production operations
remain unexecuted without their distinct approval. Preserve published preview assets.

- WP-05b/05c is actually merged via PR #11 at
  `470e7c8b0421d91ae38fbc65b888c16e70b1088c`; final PR CI `44823906492`
  and merged main CI `44824237705` succeeded. The merged tree matches the
  reviewed head. WP-11/12 starts from that verified base, not a duplicate job branch.
- WP-11/12 provides UUID catalog/member models, normalized canonical variants and
  part codes, explicit aliases with exactly one target, required protected member
  assignment, expected/optional parts and reusable independently copied templates.
  Unknown and deliberately defined empty expectations remain distinct.
- Complete authenticated German CRUD/search/pagination/detail screens include
  controlled references, explicit unused-record deletion, deactivation protection,
  optimistic conflict detection, CSRF and escaped output. Referenced musical
  identities cannot be silently retargeted. No archive files/roles are fabricated.
- Local acceptance: 265 full pytest tests, four Playwright tests, Ruff lint/format,
  Django system/migration-drift and whitespace checks passed. Separate interpreter
  migrations/reopen tests preserve identities/assignments. Browser acceptance covers
  equal titles/names, notation variants, template independence, member deactivation
  and protected references; desktop/mobile screenshots inspected.
- Full diff review, push/PR, Linux/container CI and verified merge remain the next
  gates. These source features are not claimed to be in the published 0.1.0-preview.1.
- Initial PR #12 source `32a7e065d9c1b8d562bbdc0d4b911fb56972e194` passed
  265 Linux tests and runtime audit in CI `44840283911`, but its mobile browser
  width assertion failed. Privacy-safe geometry diagnostics retained that exact
  assertion; full CI `44840633432` then passed, including all browsers and actual
  image/Compose/container/restore/security checks. An additional explicit load,
  font and animation-frame boundary removes the unsynchronized measurement after
  navigation/viewport resize. Final CI must still verify that follow-up.

- Final source `3f1b30969843f508ffda082c4f80d94155aff392` passed full CI
  `44841036938`: 265 tests, four browser tests, runtime audit, actual amd64 image,
  Compose, container/restore and vulnerability/secret checks. Full diff reviewed;
  no submitted reviews or unresolved threads. Software-verified count: 14 WPs,
  57 unfinished. Documentation checkpoint precedes authorized PR #12 integration;
  final PR CI and merged-main verification remain mandatory before WP-17.

- PR #12 merged at `a2d7264e43c823c612236e29effc414c8879cd97`; final PR CI
  `44841417182` and main CI `44841705128` passed. Merged tree equals reviewed
  head `c0d1a0af2e5cd72c5b4718412c9202e4c35a4645`. Local main: 265 tests passed.
- An additional Windows browser run exposed a concurrent job-test failure:
  Django's default shared-cache in-memory SQLite returned `database table is
  locked`. That mode does not exercise the production file DB busy timeout.
  A bounded follow-up uses an isolated temporary file DB for browser acceptance,
  and asserts that the real worker uses its canonical lock. No production DB
  settings, retry policy or browser assertions are weakened. Complete browser
  and CI gates must pass before starting WP-17.
- Follow-up local checks: all four browser tests passed; the real job lifecycle
  then passed twice independently. Ruff lint/format and whitespace passed.


## WP-17 — PDF foundation, 2026-11-21

- Resumed WP-11/12, completed PR #12 and its bounded browser test correction
  PR #13 before starting PDF work. PR #13 source
  `974348995e70ed97d8fe6eca57e300c4b547b802` passed CI `44842205008`, merged at
  `2f4b0e98bd81e4eff29b5c1326199f95c684986b`; main CI `44842489941` passed.
  Both merged trees matched reviewed heads. Catalog/member acceptance is integrated.
- Checked branches/worktrees/clean status and started
  `feature/wp-17-pdf-foundation` at that verified main. No duplicate PDF branch.
- Added locked pypdf 7.1.1 and pypdfium2 5.15.2; actual official Windows/musl
  wheels, hashes and native notices inspected. Alpine baseline is preserved.
- Pure core API accepts immutable byte snapshots, stages privately, and isolates
  every parser/native operation with memory/CPU/time/output limits. Adds bounded
  inspection/text, geometry/CropBox/UserUnit/rotation, thumbnails/PNG and ordered
  vector-preserving merge. Source/CLEAN bytes are untouched; no archive UI/OCR,
  approval, publication or generation feature is claimed.
- Reviewed active-content removal without losing Type3 glyphs/transparency.
  Unsupported visual annotations/forms fail explicitly rather than losing notation.
  Synthetic tests cover malformed/encrypted/oversize files, every major resource
  bound, compressed expansion, Unicode, A4/A3/custom rotations, effective crop,
  cancellation/private cleanup and structural/pixel preservation. A container smoke
  now exercises actual musllinux native PDF rendering in the hardened image.
- Intermediate local full suite: 316 passed, two POSIX-only skips on Windows;
  final form/active-content refinements and complete final gates are checked below.
  No Docker runtime is installed locally: image/Compose/security and Linux rlimit
  acceptance require GitHub CI. No NAS, real archive or additional release action.

- Final local full suite: 317 passed, two POSIX-only skips on Windows. All four
  Playwright browser tests passed. Latest parser/form refinements additionally
  passed targeted checks. Ruff lint/format (117 files), compilation, system,
  migration drift, locked dependency and whitespace checks passed. Full source
  diff reviewed. Synthetic PDFium and independent Poppler images visually checked
  (Poppler reported unavailable unused fallback fonts; the inspected German
  text/lines were intact). PR/Linux/container gates remain before completion.

- Source `309081c77ca296da1bdb8e1b13704da1c5aecc91`, PR #14, passed complete
  CI `44844708708`: 319 Linux tests (including POSIX gates), four browsers,
  runtime dependency audit, actual amd64 image/Compose/container/restore and
  native musllinux PDF primitives. Vulnerability/secret scan passed. No submitted
  PR reviews or unresolved threads; full diff reviewed. Software-verified count:
  15 WPs, 56 unfinished (55 required plus optional WP-43). Verify final docs CI
  and merged main before beginning the separate installation milestone.


## Simplified Synology installation — 2026-11-21

- Completed WP-17 before starting: PR #14 final head
  `27f77f8d390cf76b181fa5805f42c04e5026ddfd`, CI `44845116222`, merge
  `c12e71cc7c3d5676a5be5a4cadee1a39e6ea8cfc`; main CI `44845475304` passed.
  Merged tree matched the reviewed head. Current verified/integrated count:
  15 WPs, 56 unfinished. Published image/tag/assets remain unchanged.
- Checked root/status/worktrees/existing branches, then started separate
  `feature/synology-simple-install` from that verified main.
- Standalone `configuration.yaml` uses the published immutable digest, three
  essential edits (identity/host/origin), a fixed root with distinct subdirectories,
  no `.env` or new parser/service. All runtime protections/profiles remain.
- Guarded POSIX preparation creates only missing directories/key, validates
  actual non-admin identity/membership, canonical paths and existing modes, never
  recursively changes permissions, and refuses new keys beside existing DATA.
  Host preflight now checks RAW ownership and ancestor rename boundaries, including
  sticky-parent semantics, plus secret directory replacement denial.
- German primary guide follows eight actual first-start steps; README is concise.
  Technical diagnostics/developer/worker details were consolidated into appropriate
  docs, including correcting the obsolete pre-recovery worker description. Update,
  restore, Debug and advanced `.env` instructions distinguish the active base file.
- Future bundle packaging includes the new files and bakes the verified release
  digest into simple references without installer preprocessing or source changes.
  Historical packaging and original published assets stay unchanged.
- Local checkpoint: full pytest 321 passed / two POSIX skips, four browsers passed;
  bundle coverage expanded afterward to six passing focused tests. Ruff (120 files),
  compilation, actionlint and Bash syntax passed. Actual Compose parsing and
  root/Linux helper/container tests cannot run locally (no Docker); new CI exercises
  the published digest, real interactive provisioning, migration/restart persistence,
  host/container RAW denial, identity/mount/network limits, key preservation and
  negative preparation cases. CI has not yet run for this milestone.
- Physical DSM/Container Manager UI/ACL/TLS/firewall/filesystem/restore acceptance
  remains unperformed and separately authorized. This ops slice does not mark full
  WP-48/07/22 or other hardware-dependent packages complete. No real data or NAS use.

- Final local suite after bundle drift coverage: 323 passed, two POSIX-only skips;
  four browsers passed. Six bundle tests pass. Ruff/format, compilation,
  system/migration drift, actionlint, Bash syntax and revised local documentation
  links passed; complete diff reviewed. CI runs the first-install procedure with
  both the published immutable digest and the local candidate (no publication).
  Linux/Compose/container verification is still pending before integration.

- Source `c74e7c20ce1ee4348b6bc6e265d5517b88f2a820`, PR #15, passed full
  CI `44848131876`: 325 Linux tests, four browsers, runtime audit, actual image,
  Compose, container/restore/native PDF checks, and complete simple installation
  with both published digest and current candidate. Interactive account/password
  concealment, RAW negatives, persistence, key/data preservation and preparation
  refusal cases passed. Vulnerability/secret scan passed. Full diff reviewed;
  no submitted reviews/unresolved threads. Final docs CI/merge/main remain before
  advancing. Physical NAS gates remain separate; package count stays 15 / 56.


## Manual archive sequence — resumed 2026-11-21

- Owner reaffirmed: finish current installation first, then separate dependency-safe
  WP-13 and WP-14, continuing toward preview/index/review/search/download where
  complete acceptance and manageable integration permit. No automatic stop after
  WP-13/14, no OCR/project/printing prerequisite unless the plan requires it.
- PR #15 final head `d2dff42303f73728e75a44eed83dad235ebad5f0` passed full CI
  `44848528982`, merged at `480514264eee4aab15e77cc58447019d3a637154`; merged
  main CI `44875615555` passed. Trees match; simplified installation is integrated.
  Physical NAS acceptance and further releases remain unexecuted/unapproved.
- A local installation archive was built and inspected without publication:
  `.dev/notenarchiv-simple-install.tar.gz`, SHA-256
  `5e2c8f7f425412de4e05a0a5e2ad33ed24852c211985980869de523be26d7196`.
  It contains the exact published digest and all 14 intended regular files.
- Root/status/worktrees/upstream/existing branch were checked, then
  `feature/wp-13-archive-versions` started from verified main above. Archive app
  has only its skeleton; no implementation is assumed. WP-13 is now in progress,
  not complete. Counts remain 15 software-verified WPs / 56 unfinished.


## WP-13 � Archive versions and state model

- Separate branch from verified main `480514264eee4aab15e77cc58447019d3a637154`.
  Added protected source/file/version identities, separate base/derivative content,
  multiple part assignments, non-exclusive folder proposals, bounded local
  recognition evidence, sealed review revisions, exact per-reviewer inspections,
  audit history and job/attempt/intent-bound publication metadata.
- Short write-first services preserve approved assignments during new analysis,
  enforce explicit inspected approval and canonical receipts, reject stale edits,
  and retain withdrawn/unavailable history. Source/index/candidate/review/CLEAN
  availability are independent; no confidence-based auto-approval.
- 47 focused tests passed, including actual migration/reopen persistence,
  competing file-SQLite connections (one saved edit, one revision conflict),
  protected references, invalid states/paths/metadata, multi-part confirmation,
  stale/foreign proof, failed/wrong receipts and rollback. Four existing browser
  tests passed. Ruff lint/format (129 files), system and migration drift checks
  passed. Full regression suite and CI/integration remain in progress.
- See ARCHIVE_MODEL.md for contracts. No physical copy, ingestion, review UI or
  NAS validation is claimed by this model package. Counts remain 15 / 56 until
  full acceptance and green integration complete.

- Full regression after correcting the jobs-only SQLite test fixture: 370 passed,
  two POSIX-only skips. All ten real queue/recovery tests passed using the actual
  migrated schema; assertions and PROTECT constraints remain intact. Final diff
  review added explicit derivative approval coverage: derivatives require their
  own hash inspection and canonical publication in PROCESSED, never inherit base
  approval; all 17 workflow tests passed after this refinement. Existing four
  browser tests passed. Ruff, compilation, system/drift and whitespace checks
  passed. Ready for separate commit/PR and actual Linux/container CI.

- Source `2c91b43c06f989c205980e1acc99f84d4a8f5842` pushed on
  `feature/wp-13-archive-versions`, PR #16. Final focused suite: 48 passed.
  Full Linux CI `44881080792` passed: 373 tests (including both POSIX gates),
  four browsers, runtime audit, actual non-root amd64 image/Compose/native PDF,
  container and isolated restore, published/candidate simple first installs,
  vulnerability and secret scans. Complete diff reviewed; no submitted PR reviews
  or unresolved threads. This checkpoint precedes final documentation CI and
  exact-head integration/main verification. Integrated count remains 15 / 56
  until that gate; WP-14 has not started. No physical NAS/release action.
