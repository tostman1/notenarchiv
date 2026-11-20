# Deploy and Debug operation

Deploy is the default: no active DEBUG_MODE key in compose.yaml. Django DEBUG
is always False, in both modes. Authentication, CSRF, HTTPS cookies, path/mount
validation, non-root identity and read-only filesystems remain active.

To enable diagnostics, stop/recreate the web project with both files:

```sh
docker compose -f compose.yaml -f compose.debug.yaml up -d --force-recreate web
```

Use the same pair for one-shot tools when needed. Container Manager must apply
the equivalent merged Compose configuration; validate it first. There is no
runtime GUI toggle. This preview deploys no worker; when a worker is introduced,
both services must share the same mode and be recreated together.

Debug writes sanitized stdout and `/data/logs/web.debug.log`, with a 10 MiB
file and five backups. Only one web process owns this file. Auxiliary management
commands and the liveness helper do not contend for it. Gunicorn uses one worker,
four threads and no overlapping reload/automatic worker recycling.

Authenticated users can open Debug / Logs, filter bounded pages and download
sanitized excerpts. See [the German guide](archivist-diagnostics.de.md). Regular
future business progress/review is independent of diagnostics.

Return to Deploy using compose.yaml alone and force recreation. Existing Debug
files are preserved; the menu disappears and all diagnostic routes return 404,
including old log downloads. Do not delete logs automatically on a mode switch.
An occupied writer slot or unusable log directory must fail clearly; stop the
old process or correct permissions rather than disabling locking/security.
