# Notenarchiv & Marschbuch-Generator

A local, browser-based sheet music archive and personal music-folder generator for a music association. Digitize once, verify and organize the archive, then reuse the music for concert folders, marchbooks, entertainment folders and small ensembles.

**Status:** Specification and implementation planning. The features, installation and container image described here are target deliverables, not claims of existing functionality.  
**Target:** Synology DS224+, Docker Compose, Linux amd64.  
**Interface:** German. Technical development and documentation: English.

## What the application will do

- Index NAS PDF folders, compare filenames with actual PDF text and local OCR, propose part assignments, and require archivist visual approval. Search titles immediately, manage arrangements and confirmed versions, identify missing music, and export individual notes directly.
- Keep real, byte-identical, standardized PDF copies in a separate CLEAN archive. RAW never changes. Optional scan enhancement produces separate derivatives, with visual review.
- Maintain members, instrument variants, playable parts, replacement rules and ensemble roles.
- Save, reopen, edit and duplicate projects. Each project has exactly one shared piece list, automatic numbering and optional reserved slots. Select participating musicians from the association, including guests.
- Change personal part assignments quickly using the matrix. Pick confirmed editions with the correct notation, use project defaults and override individual pieces; batch changes and reset are direct actions.
- Produce full **personal** folders, selected project excerpts/reprints, direct archive notes and separate contents sheets. Missing parts require explicit confirmation and placeholders. Never stamp piece numbers onto music pages.
- Generate separate reading and print PDFs. Preserve native A3 pages; pair A4 portrait pages within pieces on A3 landscape. Marchbook default 170 × 120 mm. Preview and print on verified network printers, with explicit fallback if necessary.

### Example assignment matrix

| Piece | Mathias | Sebi | Riccardo |
| --- | --- | --- | --- |
| Böhmischer Traum | Posaune 1 | Posaune 2 | Posaune 3 |
| ABBA Medley | Posaune 1 | Posaune 2 | **Posaune 2** |
| Abel Tasman | Posaune 1 | Posaune 2 | **Posaune 2** |

Fictional example: Riccardo deliberately changes part on selected pieces; the other participants and shared piece list remain unchanged. A reprint for Riccardo uses the same effective assignment as his full folder.

## Data safety

```text
RAW/        existing original PDFs, read-only
CLEAN/      real byte-identical, organized copies, confirmed or clearly pending
PROCESSED/  separately approved enhanced derivatives
STATUS/     mirrored indexing/review markers, never stored in RAW
EXPORT/     generated immutable PDFs and manifests
DATA/       local SQLite database, job data, logs and cache
```

No automatic approval based on a filename or OCR confidence. Indexing is not review and review is not completeness. The application never modifies RAW. CLEAN is independently browsable as actual PDF files. See [requirements](REQUIREMENTS.md) for business rules and [architecture](ARCHITECTURE.md) for permissions, versioning and recovery.

## Technology

Python 3.12, Django 5.2 LTS, Gunicorn, WhiteNoise, HTMX, local CSS/JS, SQLite, one persistent background worker, pypdf, pypdfium2, ReportLab, OpenCV, Pillow, NumPy, Tesseract, pytest and Docker Compose. One image for web and worker, published in GitHub Container Registry after tests and approval. No external OCR, CDN, runtime cloud dependency or telemetry. Native library, licensing, NAS and printer checks remain pending.

## Documents

| File | Purpose |
| --- | --- |
| [REQUIREMENTS.md](REQUIREMENTS.md) | Normative product behavior, business rules and requirement IDs |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Technical design, data model, configuration, security, deployment |
| [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) | Ordered milestones, work packages, acceptance and tests |
| [AGENTS.md](AGENTS.md) | Instructions and approval workflow for coding agents |
| [DECISIONS.md](DECISIONS.md) | Confirmed decisions, design defaults and pending evidence |

## Delivery roadmap

1. Foundation, authentication, navigation, jobs, CI, secure container smoke test.
2. Manual archive: indexing, physical copies, review, search, direct note export.
3. Local OCR, recognition and incremental reindexing.
4. Projects, ensemble, matrix, immutable preflight and full personal/partial exports (MVP).
5. Scan enhancement and marchbook layout.
6. Printer support, backup/restore, security and release validation.

See the implementation plan for dependencies and release gates. The MVP is a useful milestone, not the full product.

## Planned development and deployment

Development uses `uv sync --locked`, `uv run pytest`, `uv run ruff check .` and `uv run ruff format --check .`. Local development selects the `local` profile explicitly (loopback-only, synthetic roots under `.dev/`): `source scripts/dev_env.sh` (POSIX) or `. ./scripts/dev_env.ps1` (PowerShell), then `uv run python manage.py migrate && uv run python manage.py runserver`. The deployment (`nas`) profile is the default and requires the full environment contract (see `.env.example`); validate it with `uv run python manage.py validate_config --service web|worker`. Follow the implementation plan before running commands that depend on files or services not yet created.

For NAS deployment, create a dedicated non-admin account `svc_notenarchiv`, determine UID/GID using `id`, prepare distinct roots and mount RAW read-only. The architecture includes the environment-variable contract and illustrative Compose configuration. Actual share paths, IDs, RAM, DSM version, DNS/HTTPS and printer support must be verified. Use an exact approved image tag/digest; never automatically deploy unreviewed changes. Installation/update/restore runbooks are deliverables of the plan.

Deploy is default. To enable application diagnostics, set the following in the environment shared by web and worker in Compose, then recreate both containers:

```yaml
environment:
  DEBUG_MODE: "TRUE"
```

Debug adds authenticated GUI logs and persistent rotating files; Django DEBUG remains False. `PRINT_ENABLED=0` until actual printer verification.

## Contributing and licensing

Follow [AGENTS.md](AGENTS.md). Use small reviewed work packages, meaningful commits and approved release/deployment steps. Test with synthetic fixtures; never put real association notes, member data, database files or secrets in the repository or external CI/AI systems. The application license and third-party notice inventory must be finalized with the owner; private use is not an exemption from dependency obligations.

### Technical diagnostics (WP-04a)

Both services read the same `DEBUG_MODE`. The web service defaults to
`NOTENARCHIV_SERVICE=web`. Set `NOTENARCHIV_SERVICE=worker` on the worker.
Deploy sends structured INFO and higher events to stdout. Debug also writes
DEBUG and higher events under `/data/logs` (local profile: `logs/` under the
development root). Each service retains its current file and five 10 MiB
backups. Only one process can own each service file. For local debugging use
`python manage.py runserver --noreload` to run a single web process.
An unavailable output directory or occupied writer slot fails Debug startup.
Changing back to Deploy preserves existing diagnostics.

Use named diagnostic events and typed fields for application logging. Raw
messages, exception details, request paths, cookies and subprocess output are
excluded from the JSON format. Request diagnostics can include the HTTP status.
