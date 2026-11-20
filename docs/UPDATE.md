# Controlled preview update and rollback

No automatic NAS update is configured. Use only an owner-approved prerelease
and the immutable GHCR digest in its release evidence. Do not use floating
`latest`, an unverified tag or a candidate's local Docker image ID.

## Update

1. Read the release notes and actual schema/storage compatibility statement.
   Download the new installation bundle and digest. Keep the old bundle/digest.
2. Stop web and finish any one-shot tools. Make and verify the full preview
   restore point in [RESTORE.md](RESTORE.md), including secret and config.
3. Change APP_IMAGE to the new approved digest. Keep host roots and the secret
   deliberate and unchanged unless a reviewed migration explicitly requires it.
4. Run host/Compose validation and `docker compose pull`. With web stopped,
   run `docker compose --profile tools run --rm migrate` once. Do not run
   migrations through a running web container or delete a live maintenance lock.
5. Recreate web with `docker compose up -d --force-recreate web`. In Container
   Manager, use the corresponding project update/recreate operation with the
   reviewed files. Merely restarting does not apply changed environment settings.
6. Verify health, HTTPS login/logout, saved accounts, UI availability and the
   effective Debug/Deploy mode. Keep the verified backup until retention is agreed.

## Rollback

A previous image alone is not a rollback if migrations or data layout changed.
Stop the failed/new web service. Preserve the changed state privately. Restore
the complete pre-update DB/secret/config snapshot into new isolated destinations
and use its exact old image digest. Verify the restored project before switching
the private reverse proxy. Do not blindly copy over the existing installation.
Changes after the backup are absent from the restored state; assess that loss
explicitly. Reverse migrations only when that exact downgrade path was tested.

This first preview has no prior production image and no file-publication
workflow. CI proves persistence, migration initialization and isolated restoration;
it does not claim the full two-version/archive-layout WP-49 rehearsal. Repeat
the controlled rehearsal when a second release with schema changes exists.
