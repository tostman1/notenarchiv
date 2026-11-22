# Preview backup and isolated restore

Historical published-image procedure only. Current source implements the complete
software-side WP-47a commands; see [BACKUP.md](BACKUP.md). No new image is published.

Scope: the web-only technical preview. Its authoritative mutable state is the
SQLite database (including accounts/sessions), protected secret and private
deployment configuration. The app cannot import or change archive files yet.
This is the early WP-47a/WP-49 safety slice, not the final archive backup system.
Before real ingestion, complete the full backup/restore and RAW gates.

## Consistent backup

1. Stop web/gateway gracefully (`docker compose stop -t 35 gateway web`); confirm both stopped.
   No migrate/admin tool may run concurrently. There is no deployed worker.
2. Choose a **new**, administrator-only directory on a privately managed
   backup destination outside DATA and the archive roots. Never reuse a live
   root or overwrite an older backup. Use 0700 permissions; no broad share access.
3. Copy the entire stopped DATA directory, protected secret and the actual
   Container Manager project file (`docker-compose.yml` / `configuration.yaml`
   for the simple method). For the advanced method include `.env` and
   `compose.yaml`. Include any applied Debug override, preparation/preflight
   scripts and `release-digest.txt` or a private record of the exact image digest
   in that new snapshot. Preserve ownership/modes and record the exact image digest.
   No file manifest substitutes for these actual copies. Logs are optional;
   copy no external music/member sources to GitHub or AI services.
4. Record SHA-256 hashes of the copied files in a private manifest. Verify the
   copies against the stopped originals; keep the manifest with the snapshot.
   DATA may contain empty lock files; their copies do not retain OS locks.
5. Restart the unchanged web project and verify its health and login.

File Station copying or an authorized local shell can perform these steps.
The operator must verify the actual DSM backup destination, ACLs, free space
and independent protection (for example an appropriate Hyper Backup task).
No production Hyper Backup task is created by this repository or release.

## Isolated restore rehearsal

1. Create new, separate test roots, DATA, config and secret locations. Keep
   the live project and its files intact. Copy the backed-up state into these
   new destinations; preserve service ownership and private secret permissions.
2. Verify copied hashes. Change the restored project file (simple) or `.env`
   (advanced) to these new paths, a
   different private project name/port and the backed-up **exact image digest**.
   Never bind the restored project to the live DATA or real archive directories.
3. Run the host preflight as the service identity (`--simple UID GID ROOT`
   for the standard directory layout, otherwise the advanced `.env` method)
   and Compose validation. Start web on the restored
   schema/image. The same archivist credentials should work; the secret and
   DB must belong to the same snapshot. Check `/healthz`, login/logout and
   application preview state.
4. Record success privately. Remove test resources only after deliberately
   confirming their canonical paths are isolated; cleanup is never automatic
   against configured NAS roots.

The Linux CI container smoke uses the actual SQLite Backup API, checks
`PRAGMA integrity_check`, copies secret/config, restores into an isolated DATA
mount and authenticates with the restored session. The NAS storage destination,
DSM ACLs and a real owner-run rehearsal remain unverified until WP-22.

RAW requires its own independent NAS backup. Once actual CLEAN/PROCESSED data,
review history, snapshots or outputs exist, this preview procedure is insufficient:
use the complete WP-47a/WP-47b consistent state/retention procedures.

The preparation helper is not a restore or upgrade tool. It never overwrites
existing state or silently regenerates a missing secret beside populated DATA.
Restore the original matching secret; do not bypass that failure with a new key.
