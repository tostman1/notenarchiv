# Consistent backup and isolated restore (WP-47a)

Commands: `backup_installation` and `restore_installation`. Linux no-follow/dir-fd
APIs are required; Windows fails closed. The immutable published preview image
does **not** contain these commands. No release or deployment is authorized here.

## Coverage and consistency

- Stop web/gateway and worker gracefully; finish admin/migration tools. Stop
  external SMB writes to CLEAN/PROCESSED/config during the capture window.
- Acquire `.maintenance.lock` and canonical `worker.lock`, then hold SQLite
  `BEGIN IMMEDIATE` throughout capture. Active services/competing writers reject
  the operation. Never delete lock files. Pending/uncertain durable effects,
  RUNNING jobs and staged/uncertain file operations require existing worker
  recovery/operator reconciliation first; backup never repairs them itself.
- SQLite Backup API plus actual CLEAN/PROCESSED/history/STATUS, unknown durable
  DATA files, explicitly selected config directory and matching Django secret.
  Exclude DATA logs/scratch/cache/thumbnails/process locks. Exports opt-in only.
- Require an existing independent RAW backup tree; compare every path/hash/size
  read-only. No missing/different copy accepted. This is content evidence, not
  proof of independent media, NAS retention or disaster resilience. RAW is never
  created, copied, modified or restored by these commands.
- New destinations only, files 0600/directories 0700, no symlinks/special files,
  bounded chunks/count/depth/bytes/time. Defaults: 100,000 entries, 50 GiB total,
  4 GiB/file, two hours. Partial failed directory retained privately; not a valid
  backup and never resumed automatically.
- Validate DB integrity/foreign keys and actual captured bytes for every
  available/confirmed/withdrawn archive reference. Missing referenced historical
  music blocks success, never silently drops protected history.
- Manifest records relative paths/sizes/hashes and exact image digest. Retain its
  SHA-256 separately in a protected private operator record. Adjacent seal detects
  accidents, not malicious replacement of both files; restore requires the trusted
  separate digest. A manifest without actual files is rejected.

## Explicit commands

Examples are not authorization/configuration of a NAS destination. During software
acceptance use new private synthetic directories, with live environment explicitly
pointing at the synthetic installation. All paths must be absolute and canonical.

```sh
python manage.py backup_installation /private-test/new-backup \
  --config-dir /private-test/config --raw-backup /private-test/independent-raw \
  --image ghcr.io/tostman1/notenarchiv@sha256:EXACT_64_HEX_DIGEST
python manage.py restore_installation /private-test/new-backup \
  /private-test/new-isolated-restore --manifest-sha256 TRUSTED_64_HEX_DIGEST
```

Container operations `backup`/`restore` delegate to these same commands. Mount
config and independent RAW copy read-only; only a separately approved destination
parent writable. Preserve non-root/read-only-root/no-network/RAW-read-only
protections. No destination or scheduled NAS task is configured in Compose.
`--include-exports`, `--max-bytes`, `--timeout` are explicit bounded options.

Config directory must contain actual project YAML, `.env`/Debug overrides where
used, image evidence and all other non-regenerable config/secrets. Use a dedicated
private directory, never an entire home/repository/archive. All its files are
copied privately; no actual installation data goes to Git/CI/logs/AI services.

## Recovery rehearsal

1. Restore to a **new** directory outside live roots/source bundle. Verify manifest,
   hashes and DB references before and after copying.
2. Result: `data/database.sqlite3`, `clean`, `processed`, `status`, `config`,
   `secrets/django.key`, optional `export`. RAW deliberately absent. Captured
   config is verbatim and may name live paths: **do not start it unchanged**.
   Deliberately remap every root, secret, private project name/port and exact
   matching approved image. Mount independently restored RAW read-only.
3. Set least-privilege ownership deliberately, preserve secret privacy, run host
   preflight and Compose validation. If exports omitted, create an empty isolated
   export directory explicitly. Never reference live EXPORT.
4. Use matching schema/image; no speculative migration. Start isolated services,
   check health, HTTPS login/logout, persisted assignments, visual previews and
   unchanged representative PDF downloads. Generated-output rehearsal belongs to
   WP-47b after generation exists, not a fabricated WP-47a result.
5. Record private source digest/time/acceptance. Cleanup and production cutover
   require deliberate separately authorized action, never automatic restore.

Software tests use actual copied deterministic synthetic PDFs, confirmed combined
assignments, rollback-journal/WAL SQLite and hardened containers. DSM ACLs, actual
backup destination/retention/fsync/hardware recovery and private archive validation
remain owner-approved private NAS gates (V-08/WP-22/WP-47b). CI never uses private NAS
data. The prior published-preview procedure remains in [RESTORE.md](RESTORE.md).
