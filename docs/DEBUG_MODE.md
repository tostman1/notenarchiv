# Deploy and Debug operation

Deploy is the default: no active DEBUG_MODE key in `configuration.yaml` or
advanced `compose.yaml`. Django DEBUG
is always False, in both modes. Authentication, CSRF, HTTPS cookies, path/mount
validation, non-root identity and read-only filesystems remain active.

To enable diagnostics, use the same active project and roots. For a simple
Container Manager project, its base is usually `docker-compose.yml` (the pasted
`configuration.yaml`). Place the unchanged `compose.debug.yaml` beside it and
merge it explicitly; validate the pair first:

```sh
docker compose -f docker-compose.yml -f compose.debug.yaml config --quiet
docker compose -f docker-compose.yml -f compose.debug.yaml up -d --force-recreate web gateway
```

With the source filename use `-f configuration.yaml` instead. For the advanced
method stop/recreate the web project with both original files:

```sh
docker compose -f compose.yaml -f compose.debug.yaml up -d --force-recreate web gateway
```

Use the same pair for one-shot tools when needed. Container Manager must apply
the equivalent merged Compose configuration; validate it first. There is no
runtime GUI toggle. This preview deploys no worker; when a worker is introduced,
both services must share the same mode and be recreated together.

The mount-free TCP gateway has no application file diagnostics in either mode;
it only forwards to fixed `web:8000`. Recreate it alongside web when applying
the project configuration. It is not a worker and has no private storage mounts.

Debug writes sanitized stdout and `/data/logs/web.debug.log`, with a 10 MiB
file and five backups. Only one web process owns this file. Auxiliary management
commands and the liveness helper do not contend for it. Gunicorn uses one worker,
four threads and no overlapping reload/automatic worker recycling.

Authenticated users can open Debug / Logs, filter bounded pages and download
sanitized excerpts. See [the German guide](archivist-diagnostics.de.md). Regular
future business progress/review is independent of diagnostics.

Return to Deploy using the same base file alone and force recreation. Remove
the override from Container Manager as well; do not switch to another project. Existing Debug
files are preserved; the menu disappears and all diagnostic routes return 404,
including old log downloads. Do not delete logs automatically on a mode switch.
An occupied writer slot or unusable log directory must fail clearly; stop the
old process or correct permissions rather than disabling locking/security.


## Technical event and reader contract

Deploy sends structured INFO-and-higher events to stdout. Debug adds
DEBUG-and-higher rotating files under `/data/logs` (local profile: the development
root's `logs/`). `NOTENARCHIV_SERVICE` distinguishes web and worker. Both share
DEBUG_MODE; management commands and liveness helpers use sanitized stdout only.
For local Debug runserver use `--noreload` to avoid a second log writer. An
unavailable log directory or occupied writer slot fails startup.

Use named events and typed diagnostic fields. Raw messages, exception details,
request paths, cookies and subprocess output are excluded. HTTP status is an
allowed typed field. See `config/diagnostics.py`; never log business/OCR content.

Authenticated `/diagnostics/` supports fixed web/worker sources, level,
component, job UUID and time filters. Page, JSON and NDJSON-download routes are
not cacheable and return 404 in Deploy. Readers scan at most 64 KiB / 100 records
per page and 1 MiB / 1000 records per download. Live polling is sequential at
two-second intervals with at most 200 visible rows. Signed source-bound cursors
expire after one hour and follow retained files across rotation; missing history
is reported. Stored fields are validated again; symlink/non-regular inputs are
excluded. These implementation details moved here from README.
