# Notenarchiv & Marschbuch-Generator

A local German-language application for a music association, targeting Synology
DS224+ / Container Manager. RAW remains read-only; reviewed music will be kept as
real hash-verified CLEAN copies, with separate derivatives and exports. Processing
stays local. Every new/changed musical version requires human visual approval.

**[Installation auf der Synology (Deutsch)](docs/INSTALL.de.md)** — the primary
first-install guide uses standalone [configuration.yaml](configuration.yaml),
three essential edits and a guarded preparation helper. No `.env` is needed for
the simple method. Actual NAS/ACL/TLS acceptance remains outstanding.

The immutable [0.1.0-preview.1 release](https://github.com/tostman1/notenarchiv/releases/tag/v0.1.0-preview.1)
provides login/logout, German navigation, health and authenticated diagnostics.
It accepts empty/synthetic test roots only. Its original install assets stay
unchanged; obtain the new simple-install files as explained in the guide.

The newer verified source additionally includes:

- Durable job recovery/cancellation and German job management.
- Works/arrangements, notation variants, parts, aliases, expected instrumentation,
  templates and members with protected regular assignments and German CRUD/search.
- Bounded isolated PDF inspection/text/rendering/merging primitives for developers.

These additions are not in the published preview image. Archive ingestion/review,
projects, OCR, music exports and printing are still unavailable. No new release,
NAS deployment or connection to real association data occurs automatically.

For usage see [Stammdaten](docs/stammdaten.de.md), [Aufträge](docs/auftraege.de.md)
and [Diagnose](docs/archivist-diagnostics.de.md). Operations: [advanced installation
and security](docs/INSTALL.md), [backup/restore](docs/RESTORE.md),
[updates](docs/UPDATE.md), [Debug mode](docs/DEBUG_MODE.md),
[release/digest evidence](docs/RELEASES.md).

Development uses Python 3.12, Django 5.2 LTS, uv, Ruff and pytest:
`uv sync --locked`, `uv run ruff check .`, `uv run ruff format --check .`,
`uv run pytest`. Browser acceptance runs separately with `uv run pytest browser/`
and the documented local Playwright setup. See [developer setup](docs/DEVELOPMENT.md),
[PDF API](docs/PDF_CORE.md), [catalog API](docs/CATALOG.md),
[archive state contract](docs/ARCHIVE_MODEL.md), [file publication](docs/FILE_PUBLICATION.md)
and [job contracts](docs/JOB_FRAMEWORK.md).

The binding project context is [requirements](REQUIREMENTS.md),
[architecture](ARCHITECTURE.md), [decisions](DECISIONS.md),
[implementation plan](IMPLEMENTATION_PLAN.md) and [agent instructions](AGENTS.md).
[Delivery sequence/counts](docs/DEVELOPMENT_SEQUENCE.md), [progress](docs/PROGRESS.md)
and [handoff](docs/HANDOFF.md) distinguish software/CI, published images and
unverified NAS gates. No real music, members, OCR, secrets or DB files belong in
Git, CI artifacts, logs or external AI services.
