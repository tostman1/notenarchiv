# Synology technical preview installation

This is an **empty/synthetic-data technical preview**, not a usable music
archive or the full M3/M6 release. Login/logout, German responsive navigation,
health and authenticated Debug diagnostics work. Archive import, editing,
OCR, projects, generation and printing are unavailable and disabled. There is
no deployed worker. Do not connect real music, members or existing archive roots.

## Release and prerequisites

Use the approved GitHub prerelease's `notenarchiv-preview-install.tar.gz` and
`release-digest.txt`. A candidate build or proposed tag is not a published image.
The digest file is generated only after GHCR push and authenticated pull succeed.
The image repository is `ghcr.io/tostman1/notenarchiv`; no `latest` tag is used.

Record the actual DSM and Container Manager versions privately. The installed
Compose implementation must accept service profiles, `read_only`, `internal`
networks and long bind syntax with `create_host_path: false`. Run the actual
`docker compose config` check below. Do not replace these safeguards with short
bind syntax to work around an old version. DS224+ must run the amd64 image.
Actual NAS/ACL, reverse-proxy and hardware validation remain WP-22; no NAS
deployment is performed by CI or by the release workflow.

Check the actual Docker engine/vendor fixes and NAS firewall privately. Docker
documents that versions older than 28.0.0 can expose localhost-published ports
to specially routed same-L2 clients. A private host-port/TLS boundary must be
verified from another LAN host (including the gateway/container route), or
protected with an effective, tested host firewall/vendor fix before installation.
Do not assume DSM's generic firewall page automatically filters Docker traffic.
See [Docker port publishing](https://docs.docker.com/engine/network/port-publishing/).

Extract the installation bundle into a private project folder, for example
`/volume1/docker/notenarchiv-preview/config`. Keep `.env` and secrets out of Git.
Web and its mount-free TCP gateway start normally; migrate/admin have the
`tools` profile. The gateway is published on **127.0.0.1:8085 only**; web has
no published port and stays on an internal network. Do not publish either directly
to the LAN or Internet. No router port forwarding is part of this preview.

## Dedicated identity and synthetic roots

Create a non-admin DSM user `svc_notenarchiv` and a dedicated group such as
`notenarchiv_service`, with only the service identity as a member. Deny
unnecessary applications/shares. Determine the real UID and dedicated group
GID through an authorized local SSH session (`id svc_notenarchiv`; use the
dedicated group's actual ID, not a guessed number or the general `users`
group). Docker uses this UID/GID explicitly; the dedicated GID may differ
from the account's ordinary primary group.

Create the following **new, empty** directories, using your actual volume:

| Example host location | Service permissions | Container path |
| --- | --- | --- |
| `/volume1/notenarchiv-preview/raw` | DSM read-only; parent not service-writable | `/archive/raw`, read-only |
| `/volume1/notenarchiv-preview/clean` | Read/execute for web | `/archive/clean`, read-only |
| `/volume1/notenarchiv-preview/processed` | Read/execute for web | `/archive/processed`, read-only |
| `/volume1/notenarchiv-preview/status` | Read/execute for web | `/archive/status`, read-only |
| `/volume1/notenarchiv-preview/export` | Read/execute for web | `/archive/export`, read-only |
| `/volume1/docker/notenarchiv-preview/data` | Service UID owner, mode 0700 | `/data`, read/write |
| `/volume1/docker/notenarchiv-preview/secrets/django_secret_key` | Admin-owned; service GID read, mode 0440 | Separate read-only secret mount |

Use distinct canonical directories with no symlink components. Never overlap
RAW/CLEAN/PROCESSED/STATUS/EXPORT/DATA, even through different bind targets.
Do not place the secret under any of these roots. Do not recursively chmod
existing archive shares, use `chmod 777`, grant administrator membership or
mount the Docker socket into the app.

For the new synthetic tree, an administrator can own the archive directories
with the service GID and modes 0550 (files 0440), with an administrator-owned
0750 parent. Configure DSM ACLs consistently; inherited group write permissions
must not make RAW writable. DATA is owned by the service UID/GID (0700).
The secrets directory is admin-owned/service-GID-readable (0750). DSM ACLs may
override POSIX expectations: verify as the actual service identity.

RAW has two independent protections: DSM filesystem permissions and the
container's read-only mount. No startup or host preflight writes into RAW.
Verify write/create/rename/delete denial on a dedicated synthetic fixture at
both layers before any future approval to attach real data.

## Registry, configuration and secret

If GHCR requires authentication, register `ghcr.io` in Container Manager with
your GitHub username and a privately stored PAT (classic), scoped to
`read:packages` and the package's access rights. Alternatively use interactive
`docker login ghcr.io -u tostman1`. Never put the token in Compose, `.env`, an
image layer, a command argument, screenshots or this repository. Package
visibility is not changed automatically.

Copy `.env.example` to `.env`. Fill APP_UID/APP_GID, the canonical host paths,
the private DNS hostname and its `https://...` trusted origin. Copy the exact
reference from `release-digest.txt` into APP_IMAGE. Keep localhost and 127.0.0.1
in the host allowlist for private liveness checks. PREVIEW_DATA_ONLY=TRUE is
your acknowledgement that only empty/synthetic roots are attached. Do not
source `.env` as a shell script; the supplied preflight reads values as data.

Generate a strong random secret locally and store it directly in the protected
secret file. One method after pulling the approved digest is the following
(replace IMAGE and SECRET_FILE locally; no real values belong in chat):

```sh
( set -C; umask 077
  docker run --rm --log-driver=none --network=none --read-only \
    --cap-drop=ALL --entrypoint python IMAGE \
    -c 'import secrets; print(secrets.token_urlsafe(64))' > SECRET_FILE
)
```

The redirect must target a newly created protected file as its administrator;
do not overwrite an existing installation's secret. Set its owner/GID and mode
0440 as described above. The logging driver is disabled so the generated key
is not retained in container logs. Back it up privately; changing it invalidates
sessions. The key is read from a file, never from an environment value.

Make the configuration readable by the service GID but not service-writable,
e.g. administrator owner/service GID, mode 0640, with a traversable protected
parent. From the extracted bundle, run these checks on the NAS:

```sh
sudo -u svc_notenarchiv -g notenarchiv_service sh scripts/preflight-host.sh /absolute/path/to/.env
docker compose --env-file .env config --quiet
docker compose --env-file .env pull
```

The host check requires `sh`, `awk`, `grep`, `readlink`, `id` and `dirname`.
It verifies canonical distinct host sources and RAW access as the service
identity without creating test files in RAW. Container startup separately
checks actual mount identities, read-only flags, root filesystem, secret
permissions and service-specific DATA write access. Neither check substitutes
for the private DSM synthetic ACL acceptance.

## First start and account provisioning

Run migrations once with web stopped, then create an archivist interactively:

```sh
docker compose --env-file .env --profile tools run --rm migrate
docker compose --env-file .env --profile tools run --rm admin
```

Enter username and password at the private terminal. Password input is hidden;
the admin service has logging disabled. No password argument, random-password
stdout, automatic default account or plaintext credential file is supported
by the container entrypoint. All archivists have the same business rights;
there is no Django admin site. To change an existing password while web is
stopped, use `... run --rm admin provision --set-password`.

In DSM **Container Manager → Project**, create/import a project from the
extracted folder and `compose.yaml`, using `.env` beside it. Keep it stopped
until the preceding one-shot steps finish. Start the project normally; only
web plus the gateway start. Exact wizard labels vary by installed DSM/package version.
The equivalent command is `docker compose --env-file .env up -d web gateway`.
An uninitialized database causes safe startup failure; web never auto-migrates.
Migrations and provisioning refuse to run while web holds its maintenance lock.

## Private HTTPS reverse proxy

In DSM's Login Portal / Advanced reverse-proxy settings, configure your private
HTTPS hostname and certificate to forward to `http://127.0.0.1:8085`. Explicitly
overwrite `X-Forwarded-Proto` with `https`; do not forward a client-supplied
value unchanged. Restrict access to the private LAN or approved private remote
access. Use a certificate trusted by your browser (private CA or an appropriate
NAS-managed certificate). Do not disable secure cookies, CSRF or Django security
to work around a certificate/proxy error.

The backend trusts this private proxy header because only the mount-free
gateway bridges its internal network to the loopback host port. Do not attach
untrusted containers to those networks. The gateway uses the same image, has
no data/secret/archive mounts, forwards only to fixed `web:8000`, and bounds
connections/time/buffer use. Direct HTTP business requests redirect to HTTPS. `/healthz` is
the only non-sensitive redirect exemption; it returns no DB or personal data.

This transport is necessary because an internal-only Docker network has no
default gateway and does not publish host ports. Web remains internally
isolated; the gateway alone joins a separate frontend bridge. See the
[Docker maintainer explanation](https://github.com/moby/moby/discussions/53256).
It is not a processing worker or an additional image dependency.

## First-start acceptance (record privately)

- Container reports healthy; `docker compose exec -T web python -m scripts.healthcheck`
  succeeds. Image digest and runtime UID/GID match the approved values.
- `https://YOUR_PRIVATE_HOST/healthz` returns `{"status":"ok"}`; no login,
  database contents or trace is exposed there.
- HTTP business URLs redirect to HTTPS. Unauthenticated home redirects to login;
  login/logout and German navigation work over the private HTTPS hostname.
- The preview banner is visible. Unimplemented navigation is disabled and
  labelled "In Entwicklung" / "Noch nicht verfügbar". No import or processing
  action is available; no worker is running.
- Restart web; the account and session survive. Verify DATA is persistent.
- Direct `/diagnostics/`, `/diagnostics/records/` and `/diagnostics/download/`
  return 404 in Deploy. Follow DEBUG_MODE.md for an authorized Debug test;
  Django DEBUG remains False and old logs survive returning to Deploy.
- Verify RAW host ACL and mount negatives on synthetic fixtures and record
  actual DSM/Container Manager/Compose versions, CPU/RAM and filesystem evidence.
- Perform the isolated backup/restore rehearsal in RESTORE.md before updates.

The automated Linux container smoke exercises these software paths with
synthetic inputs. It does **not** prove this NAS's ACLs, DSM UI, TLS certificate,
backup destination or hardware capacity. Those checks remain the private WP-22
gate. Real-data ingestion additionally requires the complete WP-47a safety gate.

## Troubleshooting and upstream references

Use `docker compose ps` and bounded container logs locally. Do not upload DB,
secrets, actual OCR/music or personal data to issues or AI tools. Startup
rejection usually means a missing host directory, unsafe mount/secret mode,
root identity, missing migration, or occupied maintenance lock. Fix the cause;
never disable validation or remove a live process lock file.

The host-side preflight catches path/identity errors; the container-side check
cannot prove DSM ACLs. A redirect loop means the proxy header/certificate/host
configuration needs correction, not Django DEBUG or insecure cookies.

References checked 2026-11-20:
[Synology Project documentation](https://kb.synology.com/en-global/DSM/help/ContainerManager/docker_project),
[Docker bind mounts](https://docs.docker.com/engine/storage/bind-mounts/),
[GHCR authentication and digests](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry).
