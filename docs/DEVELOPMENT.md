# Local development and verification

Use Python 3.12 and uv. `uv sync --locked` installs the pinned environment.
The default profile is NAS and fails closed without its deployment contract.
Select the local loopback/synthetic profile explicitly:

```sh
source scripts/dev_env.sh
uv run python manage.py migrate
uv run python manage.py collectstatic --noinput
uv run python manage.py runserver
```

On PowerShell use `. ./scripts/dev_env.ps1` before the same uv commands. Local
state is git-ignored under `.dev`; never point it at actual association data.
Django DEBUG stays false. Provision a synthetic archivist interactively with
`uv run python manage.py create_archivist`. Never use real member/password data.

Run `uv run ruff check .`, `uv run ruff format --check .` and `uv run pytest`.
Browser acceptance is a separate invocation: `uv run pytest browser/`. It uses
an isolated temporary file SQLite database for concurrent web/worker activity.
Install the CI-pinned `playwright-core@1.62.1` into a private `.dev/browser`
directory with npm, expose its `node_modules` through `NODE_PATH`, and provide
a local Chrome installation (`BROWSER_CHANNEL` defaults to `chrome`). Browser
fixtures abort requests outside the local test server. Do not weaken auth/CSRF
or network restrictions to run tests.

The GitHub workflow additionally audits runtime dependencies, builds the pinned
amd64 image, parses Compose, exercises actual hardened containers/restore/native
PDF processing and the simple first-install procedure, then scans vulnerabilities
and secrets. Docker-dependent tests require an isolated Linux Docker host; the
root-only synthetic smoke scripts must never target a NAS or production roots.
CI evidence does not establish physical DSM, ACL, TLS or load acceptance.

See [delivery sequence](DEVELOPMENT_SEQUENCE.md), [progress](PROGRESS.md),
[handoff](HANDOFF.md), [license inventory](LICENSES.md) and the domain API documents.
Normal users start with [the German installation guide](INSTALL.de.md).


For an installed Edge browser use `BROWSER_CHANNEL=msedge`. Validate the actual
NAS configuration with `uv run python manage.py validate_config --service web`
or `--service worker` only in its corresponding environment. This does not
perform NAS deployment or establish host ACL acceptance.

Follow AGENTS.md for reviewed feature branches and authorized release/deployment
steps. The application license remains an owner decision; preserve third-party
licenses/notices, including native libraries and fonts. Private use does not
remove dependency notice obligations.
