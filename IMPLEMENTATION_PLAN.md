# Notenarchiv & Marschbuch-Generator — Implementation plan

**Revision:** 2.0 — 2026-11-19  
**Status:** Ready for owner review; no work package is represented as implemented.  
**Scope:** Independent development on the basis of `REQUIREMENTS.md`, `ARCHITECTURE.md`, `DECISIONS.md` and `AGENTS.md`.

## 1. Delivery strategy

Build a working vertical slice early: authenticate, index a synthetic source folder into real CLEAN files, visually confirm an assignment, find and download the note. Add the project workflow and PDF output next. Do not wait for perfect OCR or printer support to make the archive useful. Each package is small enough to implement, test and review independently; larger areas use suffix IDs. Existing numbered work-package identifiers are retained where practical; numeric order is **not** execution order. Dependencies and the ordered phase lists are authoritative. All statuses initially Planned; use the work package ID in subsequent progress records.

| Phase | Deliverable / exit gate |
| --- | --- |
| M0 Foundation | Local web/worker image, authentication and navigation, safe config, minimum CI, synthetic NAS smoke, early printer capability spike. |
| M1 Manual archive | Real verified copies, source tracking, manual content review, search, completeness, preferred editions, direct note download; backup ready before real ingestion. |
| M2 Recognition | Local OCR, separate OCR job, candidate matching, review evidence, changed-version handling, measured limits. |
| M3 Personal folders (MVP) | Shared project list, participants, ensemble support, matrix, preflight/snapshots, personal full and excerpt exports, contents-only, reading and regular print PDFs. |
| M4 Scan and marchbook | Safe staged image enhancement, separate approved derivatives, marchbook layout with configurable size. Optional numbered-folder adapter after core delivery. |
| M5 Printing | Verified adapter, ordered media submissions, preview and explicit fallback, no unsafe retry. |
| M6 Operations / release | Consistent backup/restore, install/update/rollback, security/performance/license and product acceptance. |

M3 is the useful personal-folder MVP. M4–M6 remain required for the full product except specifically optional items. If a printer/hardware gate remains blocked, an explicitly scoped preview release may be approved; do not claim full completion. Exact version tags are chosen at release; use `v0.1.0` provisionally for the first accepted release, not as a promise that all functions exist. Before touching real archives complete WP-47a and the RAW/ACL negative tests. NAS operations require actual owner-approved access and synthetic test roots first.

### How to use this plan

- Start with WP-01 after owner approval; no further broad redesign required. For subsequent packages, inspect actual Git state, read relevant IDs and satisfy listed dependencies. Work on one approved package or tightly related subset at a time.
- Each row below defines **implementation scope**, **dependencies**, **acceptance/test** and **requirements**. Scope estimates S/M/L describe relative complexity only, not agent time guarantees. Required unless marked Optional or validation-only. All packages include relevant unit/integration tests, actual lint/test results, traceability updates and diff review as applicable. If a tool or environment is unavailable, document the missing verification instead of marking done.
- A package that needs new dependencies updates the lockfile and license inventory. Add browser tests when UI behavior is implemented. Hardware-specific validation runs locally using synthetic and separately approved representative real inputs; no real data enters CI.
- Approval procedure: follow the owner authorization recorded in AGENTS.md and DEC-08 (2026-11-20). Routine commits, pushes, PRs and merges within agreed implementation scope proceed after successful checks/CI and review without repeated approval. Escalate genuinely blocking decisions and actions beyond the authorized scope.

### First deployable technical preview — owner priority shift, 2026-11-20

DEC-09 authorizes implementation of a web-only, empty/synthetic-data preview
before the complete M0/manual-archive product. Existing WP IDs and full-scope
dependencies below remain authoritative; no feature is removed.

Execution: integrate/CI-verify existing WP-05a, then group the tightly related
WP-09 → WP-06 (web image slice) → WP-07 (web/tools Compose slice) → WP-08 →
WP-10. In the same bounded delivery, prepare the preview-specific backup,
installation and rollback slices of WP-47a/WP-48/WP-49. Do not claim those
full packages complete before their original archive/NAS acceptance is met.

WP-05b is a genuine prerequisite for deploying the processing worker, not
for the existing authenticated web shell. Therefore the preview omits worker
deployment and all enqueue/processing actions; WP-06/WP-07 remain partial
against the full web+worker baseline. The container still contains the shared
code/image foundation. No OCR/print/PDF native tools are added just for startup.

Preview release gate: green locked lint/unit/browser checks, real Linux/amd64
non-root image build, strict mount/identity/secret/config startup checks,
read-only root, synthetic host+mount RAW negatives, migrations, actual HTTP
login/logout/CSRF/host/HTTPS-proxy behavior, persistence, Debug switching,
isolated DB/secret/config restore, image/dependency/secret scans, SBOM and
reviewed install/update/rollback instructions. Publish only an approved
prerelease tag on main and report the verified GHCR digest; never label a
candidate as published or a preview as the completed application.

Physical installation and DSM ACL/TLS/hardware evidence are the separately
authorized WP-22 preview slice. Full WP-22 still needs worker/job UI validation.
No live NAS operation or real music/member data is authorized by this priority
shift. Full WP-47a and the original RAW/backup gates precede real ingestion.

See docs/DEVELOPMENT_SEQUENCE.md for all 71 packages, counts and parallel lanes.

### Current-feature synthetic Synology distribution — 2026-11-24

DEC-10 authorizes a standalone test deployment/release package from verified
integrated main through WP-39. This is not the next unfinished business package
and does not start OCR, enhancement, marchbook or printing work. Extend the
existing image/Compose/release infrastructure with the durable worker, guarded
isolated binds/secret, one-shot initialization, German installation/demo guide
and accurate minimal availability UI. Preserve every integrity/security rule.

Release gate: final-head Foundation/browser and Container/security checks,
actual NAS-profile Linux/amd64 Compose stack through private TLS, interactive
account, indexing/visual review/publication, projects/ensemble/matrix, preflight/
missing decisions, immutable pins, reading/regular print/excerpt/contents PDFs,
authorized downloads, worker crash recovery/cancellation/failure, host+mount RAW
negatives and persistence. Merge only after these pass; verify post-merge main.
Publish a new test-only tag by promoting the exact tested image artifact, pull
and exercise its digest, sign provenance/SBOM and package the digest-pinned
standalone install YAML. No stable/latest tag, old-preview mutation or NAS access.
Actual DSM/ACL/network/TLS/resources/SQLite/restore remain explicit hardware gates.
Record evidence in docs/PROGRESS.md and docs/RELEASES.md, then stop this package.

## 2. Work packages by execution phase
## M0 — Foundation and deployment baseline

### WP-01 — Repository, development tooling and minimal CI

**Complexity:** S · **Priority:** Required · **Depends on:** None  
**Requirements:** OP-06

**Implement:** Inspect the actual repository/branch and existing user changes; create `pyproject.toml`, `uv.lock`, Ruff/pytest config, `.gitignore`, `.dockerignore`, synthetic smoke test and `.github/workflows/ci.yml`. Pin Python 3.12 and Django 5.2 LTS foundation after compatibility check; only install needed initial packages. Preserve the specification docs; add no license with invented ownership. Use an English commit proposal.

**Acceptance / tests:** Fresh `uv sync --locked`; lock check; Ruff lint/format; meaningful import/config smoke; CI workflow runs lint and pytest on PR/push. No secret or real archive files. See section 3 for full checklist.

### WP-02 — Django skeleton and configuration

**Complexity:** M · **Priority:** Required · **Depends on:** WP-01  
**Requirements:** OP-01, OP-03, OP-04

**Implement:** Create `manage.py`, config and app boundaries, env parser, local SQLite, protected secret-file config, static assets configuration, health endpoint and management-command validation modes. Set Django DEBUG=False regardless of mode. Separate local synthetic dev from NAS profile.

**Acceptance / tests:** Settings tests for absent/TRUE/FALSE/mixed case/empty/invalid DEBUG_MODE, missing secrets and invalid host settings; minimal health response; Django system check. No production traceback.

### WP-03 — Authentication and session baseline

**Complexity:** M · **Priority:** Required · **Depends on:** WP-02  
**Requirements:** UI-01, OP-03

**Implement:** Django login/logout, protected business views, CSRF, secure HTTPS cookie settings, host validation, login rate limit, safe initial account provisioning. No differentiated business role model.

**Acceptance / tests:** Unauthenticated access rejected, CSRF enforced, password hashed, HTTPS config verified, no secret logging; authorized browser login works.

### WP-03a — Early application shell and navigation

**Complexity:** S · **Priority:** Required · **Depends on:** WP-03  
**Requirements:** UI-02, UI-03

**Implement:** German base template, navigation, empty states, feedback, accessibility, local assets and honest disabled placeholders for unimplemented features. Add initial Playwright smoke and i18n mechanism.

**Acceptance / tests:** Navigation/auth smoke in browser, local assets load offline, unimplemented modules not presented as available.

### WP-04a — Technical logging and mode contract

**Complexity:** S · **Priority:** Required · **Depends on:** WP-02  
**Requirements:** GR-13, OP-04

**Implement:** Structured/sanitized stdout logs, shared mode parsing, separate rotating files only in Debug, one writer per file, log directory permission handling and rotation limits.

**Acceptance / tests:** Deploy creates no new debug files; Debug persists and rotates logs; restart preserves files; invalid settings fail; secrets/OCR content absent from logs.

### WP-04b — Authenticated debug UI

**Complexity:** M · **Priority:** Required · **Depends on:** WP-04a, WP-03a  
**Requirements:** OP-04

**Implement:** Add mode badge, bounded live polling, filters, sanitized download; gate routes server-side and remove menu in Deploy. Use opaque IDs, not arbitrary log paths.

**Acceptance / tests:** GUI only available in Debug and authenticated; Deploy denies route even if old logs exist; pagination/escaping/filter tests; regular status remains available.

### WP-05a — Durable queue, claim and singleton worker

**Complexity:** M · **Priority:** Required · **Depends on:** WP-02  
**Requirements:** OP-02

**Implement:** Job model, status machine, payload validation, atomic conditional SQLite claim, global single-heavy-job lease, heartbeat/attempt tokens, worker command, healthcheck.

**Acceptance / tests:** Race tests on separate file-backed SQLite connections; exactly one active claimant; expired/stale attempt cannot commit state; health freshness test.

### WP-05b — Job recovery, cancellation and operation contract

**Complexity:** M · **Priority:** Required · **Depends on:** WP-05a  
**Requirements:** OP-02, PT-05

**Implement:** Lease recovery, fenced publication interface, retry policies, durable intent reconciliation hooks, safe cancellation and subprocess cleanup. PRINT unknown status and no retry.

**Acceptance / tests:** Simulated crash/restart, old attempt rejected, cancel transitions only after stop, safe handler retries idempotent, print acceptance uncertainty not auto-repeated.

### WP-05c — Job UI and progress

**Complexity:** S · **Priority:** Required · **Depends on:** WP-05b, WP-03a  
**Requirements:** UI-03, OP-02

**Implement:** Job list/detail, progress, sanitized errors, cancel button, refresh and worker availability indicator.

**Acceptance / tests:** Browser test shows queued/running/finished/failed states and real cancellation behavior; no stack trace.

### WP-09 — Service-aware mount and startup validation

**Complexity:** M · **Priority:** Required · **Depends on:** WP-02, WP-04a  
**Requirements:** GR-01, OP-03

**Implement:** Host preflight for distinct canonical roots and existing mounts; container validation for service-specific paths, mount identity/read-only flags and secret file. Web only checks writable DATA; worker checks managed write roots. No actual write probes on real RAW.

**Acceptance / tests:** Synthetic negative cases: overlap, missing mount, symlink/escape, incorrect flags, permissions; web read-only roots pass; worker unsafe setup fails clearly.

### WP-06 — Minimal hardened container image

**Complexity:** M · **Priority:** Required · **Depends on:** WP-02, WP-03a, WP-04a, WP-05b, WP-09  
**Requirements:** OP-01, OP-03, OP-06

**Implement:** Pinned base image, locked install, non-root runtime, local static collection, explicit PID/signal handling. Add PDF/OCR OS packages only when their package needs them.

**Acceptance / tests:** amd64 build, non-root, read-only root compatibility, no secrets in layers, health check and offline startup in synthetic environment.

### WP-07 — Compose services and data roots

**Complexity:** M · **Priority:** Required · **Depends on:** WP-06, WP-09  
**Requirements:** GR-01, OP-03, OP-04

**Implement:** Actual `compose.yaml`, `.env.example`, separate mounts for RAW/CLEAN/PROCESSED/STATUS/EXPORT/DATA/secrets, read-only web archive access, worker write roots, one-shot migration/bootstrap process; shared DEBUG_MODE optional entry absent by default.

**Acceptance / tests:** Compose config validated; mount matrix verified on synthetic shares, migration once, web/worker healthy, mode switching via recreate with same image.

### WP-08 — Extended CI and container verification

**Complexity:** S · **Priority:** Required · **Depends on:** WP-07, WP-03a  
**Requirements:** OP-06

**Implement:** Extend initial CI with image build/smoke, browser checks and security/secret scans; pin actions, keep synthetic fixtures only. Check actual branch protection availability with owner.

**Acceptance / tests:** CI checks demonstrate actual runs; no real data/artifact secrets, required tests not silently skipped; failure propagation verified.

### WP-10 — Versioned container release pipeline

**Complexity:** S · **Priority:** Required · **Depends on:** WP-08  
**Requirements:** OP-06

**Implement:** Approved tag on main triggers mandatory checks and amd64 build; GHCR publish uses scoped job permissions, immutable tags/digest, SBOM/notice strategy. No automatic NAS deployment.

**Acceptance / tests:** Dry-run/build test; actual registry publish only on approved test/release tag; verify image metadata and permissions when authorized.

### WP-22 — Early NAS synthetic smoke

**Complexity:** M · **Priority:** Required · **Depends on:** WP-07, WP-08, WP-04b, WP-05c  
**Requirements:** OP-01, OP-02, OP-03, OP-04

**Implement:** Measure actual DSM/RAM, create service account and separate synthetic roots on authorized NAS, verify UID/GID/ACL, mount topology, SQLite local storage/WAL, startup/login/worker, mode switch. Document evidence.

**Acceptance / tests:** Negative RAW write/rename/delete on synthetic test volume fails at DSM and mount; service rights correct; browser/worker health and resource data recorded. Real data not required. If no access, record blocked hardware gate and continue local work.

### WP-44a — Early printer capability spike (validation only)

**Complexity:** S · **Priority:** Required · **Depends on:** WP-22  
**Requirements:** PT-03, PT-04

**Implement:** Identify approved internal printers, query actual IPP/CUPS and formats, printable margins, media/order/status and marchbook custom support using safe test sheets with permission. Keep PRINT_ENABLED=0.

**Acceptance / tests:** Document actual capabilities and chosen adapter or exact blocker. No assumed DSM print service or production printer submission without approval.

## M1 — Catalog and usable manual archive

### WP-11 — Musical catalog and expected-parts CRUD

**Complexity:** M · **Priority:** Required · **Depends on:** WP-02, WP-03a  
**Requirements:** CAT-01, CAT-04, AR-07, AR-16, UI-04

**Implement:** Models/CRUD for works, arrangements, instrument variants, parts, aliases, expected parts and reusable instrumentation templates. Safe deactivation and duplicate human names.

**Acceptance / tests:** Constraints and forms tested: same titles distinct works; same instrument name with different notation distinct; no arbitrary assignments; template copy and unknown expectations verified.

### WP-12 — Membership and regular assignments

**Complexity:** S · **Priority:** Required · **Depends on:** WP-11  
**Requirements:** CAT-02

**Implement:** Member CRUD, exactly one required regular part, equal names supported, active flag and deactivation protection. Guests handled per project later.

**Acceptance / tests:** Required part and protected reference tests; searchable German forms; equal names do not merge.

### WP-13 — Archive versions and state model

**Complexity:** M · **Priority:** Required · **Depends on:** WP-11  
**Requirements:** GR-02–06, AR-03, AR-06, AR-14

**Implement:** Create source folders/files/versions, archive file with arrangement FK, assignments, recognition candidates, inspection/audit/operation entities and independent status dimensions. Define review and publication transitions.

**Acceptance / tests:** DB tests for same-content versions, multiple assignments, pending arrangement allowed but not usable, orthogonal state and protected references.

### WP-14 — Safe file copy, naming and publication

**Complexity:** M · **Priority:** Required · **Depends on:** WP-13, WP-05b  
**Requirements:** GR-01, GR-02, AR-02–06

**Implement:** Implement streaming verified copy, source stability checks, safe path handling, SMB-safe names and collision handling, operation intents, no-clobber publication and reconciliation. Keep base files immutable and separate derivatives.

**Acceptance / tests:** Hash equality even when name already correct; collisions preserve both files; source mutation detected; traversal/symlink cases denied; crash between file/DB writes recovered; RAW untouched.

### WP-17 — PDF processing foundation

**Complexity:** M · **Priority:** Required · **Depends on:** WP-01  
**Requirements:** AR-01, AR-08, EX-07, OP-02

**Implement:** Add pinned PDF libraries, validate, page size/rotation/CropBox/UserUnit, text extraction, bounded rendering, thumbnails and merge primitives in core/pdf. Synthetic PDFs generated with licensed font/assets.

**Acceptance / tests:** Scanned vs text PDFs, A4/A3/landscape/rotated and malformed/oversize fixtures, page/pixel limits and no unnecessary rasterization verified.

### WP-19 — Filename and text-layer recognition

**Complexity:** M · **Priority:** Required · **Depends on:** WP-13, WP-17  
**Requirements:** AR-08–11

**Implement:** Implement normalizer, alias/rule service, Roman numerals and combined parts, content comparison, candidate evidence and version. No OCR yet; unresolved scanned files stay pending visual review.

**Acceptance / tests:** Matches, conflicts, unknown, Posaune1 with actual Posaune2, Trombone II/III and Unicode/notation cases; no candidate auto-confirms.

### WP-15 — Indexing and separate STATUS publication

**Complexity:** M · **Priority:** Required · **Depends on:** WP-14, WP-17, WP-19, WP-05c  
**Requirements:** AR-01–06, AR-08, AR-14

**Implement:** Inventory selected folder/archive, source hashes and metadata, verified copies, filename/text candidates, operation recovery, separate marker tree and progress. Unknown assignment to pending area.

**Acceptance / tests:** Complete new synthetic import, verified files, RAW before/after identical, status visible, corrupt/changed/missing sources reported, no unreviewed assignment usable. No marker in RAW.

### WP-16 — Indexing UI

**Complexity:** S · **Priority:** Required · **Depends on:** WP-15, WP-03a  
**Requirements:** AR-04, UI-03

**Implement:** Source folder overview, selected/all index action, job status, review count, clear German instruction to inspect parts, integrity action placeholder until WP-27.

**Acceptance / tests:** E2E index -> visible status/marker -> review queue; errors/cancellation clearly shown.

### WP-18 — Secure PDF preview

**Complexity:** M · **Priority:** Required · **Depends on:** WP-17, WP-13, WP-03a  
**Requirements:** AR-12, OP-03

**Implement:** Bundle PDF.js local viewer with navigation/zoom and safe authenticated ID-based routes; bounded thumbnails; disable active scripting and restrict content.

**Acceptance / tests:** Preview from CLEAN pending and confirmed fixture; anonymous, arbitrary path and unrelated ID manipulation denied; no external requests.

### WP-20a — Individual review and publication

**Complexity:** M · **Priority:** Required · **Depends on:** WP-15, WP-18, WP-19  
**Requirements:** GR-03–05, AR-12–14

**Implement:** Review list/detail, actual PDF and filename/content evidence side by side, edit arrangement/parts, explicit inspected action, confirm via durable publish operation. Audit, canonical rename only in CLEAN, mark usable after success.

**Acceptance / tests:** Mismatch correction, combined assignment, filename-only scan visually inspected; failed publish stays unavailable; reload persistence; RAW unchanged.

### WP-20b — Efficient review and batch approval

**Complexity:** S · **Priority:** Required · **Depends on:** WP-20a  
**Requirements:** AR-13

**Implement:** Previous/next navigation, inspected/version/revision records, batch select inspected files, validate every approval server-side; clear conflicts.

**Acceptance / tests:** Batch rejects uninspected/stale proposal versions; opening preview is insufficient; approved inspected versions persist; no automatic approval.

### WP-21 — Library search and completeness

**Complexity:** M · **Priority:** Required · **Depends on:** WP-20a, WP-11  
**Requirements:** AR-15, AR-16

**Implement:** Substring title/alias search, normalization, filters, arrangement/part overview, expectation templates and completeness state.

**Acceptance / tests:** Search `ab` matches prefix and interior; distinct unknown/not required/unreviewed/missing/available; review does not imply complete; browser workflow.

### WP-23a — Preferred archive editions

**Complexity:** S · **Priority:** Required · **Depends on:** WP-20a, WP-21  
**Requirements:** AR-17, AS-05

**Implement:** List confirmed versions, notation and key, choose archive preference per arrangement/part; protect old versions, show ambiguity and withdrawal.

**Acceptance / tests:** Several versions coexist, one preference constraint; incompatible/pending selection rejected; explicit selection still valid when preference changes.

### WP-23b — Direct archive note download

**Complexity:** M · **Priority:** Required · **Depends on:** WP-23a, WP-18, WP-17, WP-05c  
**Requirements:** AR-18, EX-03, EX-07

**Implement:** Select one/multiple confirmed versions with preview; direct download of existing verified PDFs and optional ZIP of selected immutable versions. No project/member required. Validate selections and hashes, use bounded streaming; no accidental duplicate combined parts. Defer generated combined PDFs and persisted output artifacts until the shared snapshot/builder work in M3.

**Acceptance / tests:** Download confirmed combined part unchanged as a single note where selected; multi-selection and no project dependency; unconfirmed denied; no RAW/CLEAN modifications.

### WP-47a — Initial consistent backup and restore safety

**Complexity:** M · **Priority:** Required · **Depends on:** WP-15, WP-20a  
**Requirements:** OP-05

**Implement:** Before real archive ingestion, provide quiesce/write barrier and SQLite backup plus actual CLEAN/PROCESSED/config/secrets data capture; independent RAW backup check, manifest, isolated restore command/runbook.

**Acceptance / tests:** Restore DB and real copied synthetic files together, verify hashes/assignments; manifest without actual files rejected; no overwrite live RAW. Hardware backup destination pending owner approval.

## M2 — OCR and version reconciliation

### WP-24 — Bounded local OCR engine

**Complexity:** M · **Priority:** Required · **Depends on:** WP-17, WP-06  
**Requirements:** AR-08–11, OP-02

**Implement:** Add pinned Tesseract and pytesseract, language packs, per-region timeout, image preprocessing, heading detection and expansion, OCR evidence and caching by file hash/profile/rule version. Extend container and CI.

**Acceptance / tests:** Synthetic noisy/skewed headings yield candidate text/boxes; no network; timeout, resource limits, language failure and caching tests. OCR not skipped for named scans.

### WP-25 — OCR job and rule integration

**Complexity:** M · **Priority:** Required · **Depends on:** WP-24, WP-15, WP-19  
**Requirements:** AR-09–11

**Implement:** Separate OCR launch for file/folder/archive; index may enqueue suitable OCR, compare evidence, versioned rule/alias editing, uncertainty handling, retry only safe jobs.

**Acceptance / tests:** Start OCR independently, combine with text/filename, weak/conflicting evidence stays pending. Existing confirmed assignment not silently replaced by reanalysis.

### WP-26 — OCR evidence review UI

**Complexity:** S · **Priority:** Required · **Depends on:** WP-25, WP-20b  
**Requirements:** AR-12–13

**Implement:** Show relevant OCR excerpt/region, confidence, source and conflict reason in normal UI, efficient visual navigation; redact technical logs.

**Acceptance / tests:** OCR evidence available in Deploy and Debug; conflicts easily corrected; approval still requires inspection; no full OCR text in logs.

### WP-27 — Incremental reindex, integrity and version lifecycle

**Complexity:** M · **Priority:** Required · **Depends on:** WP-15, WP-23a, WP-25  
**Requirements:** GR-06, AR-05, AR-14, AR-17

**Implement:** Reindex new/changed/missing sources; retain old confirmed files; full hash integrity job, reconcile orphan operations, status update and targeted reanalysis. Publish only new reviewed versions; track preference changes.

**Acceptance / tests:** Unchanged hash no routine reprocessing; changed bytes even with same name need review, full scan catches same-size/mtime changes; deletion does not erase copies; corruption surfaced; prior version still referencable.

### WP-28 — OCR quality and NAS resource measurement

**Complexity:** S · **Priority:** Required · **Depends on:** WP-25, WP-22  
**Requirements:** AR-08, OP-02

**Implement:** Benchmark synthetic and authorized representative real inputs locally; assess OCR region/thresholds, language, thread count, memory and timeouts.

**Acceptance / tests:** Document results and tune defaults, list known failures; no universal accuracy claim; no real scan in repo. Hardware verification blocked if access absent.

## M3 — Projects, assignment and PDF MVP

### WP-29 — Project model, revisions, CRUD and duplication

**Complexity:** M · **Priority:** Required · **Depends on:** WP-11, WP-12, WP-13, WP-03a  
**Requirements:** PR-01, PR-05, PR-07

**Implement:** Project, position, participant, role, overrides and preference models; cross-project/SQLite uniqueness constraints, optimistic revision, duplicate with remapped IDs, archive/deactivate.

**Acceptance / tests:** Persistence, clone mapping, concurrent stale write rejection, reserve IDs and same-title projects; no personal list model.

### WP-30 — Shared piece list and automatic numbering

**Complexity:** M · **Priority:** Required · **Depends on:** WP-29, WP-21  
**Requirements:** GR-07, GR-12, PR-02–03, PR-06

**Implement:** Live library selection, drag/drop, explicit reserve slots, repeated arrangements, insert/remove/fill/replace, atomic reordering and derived numbering, contents preview. Preserve stable position identity and revalidate overrides on replace.

**Acceptance / tests:** Reordering 3→1 renumbers automatically; reserve consumes number but no sheet; duplicate independent IDs; replacement at same slot preserves number; no individual list.

### WP-31 — Participants and saved project defaults

**Complexity:** S · **Priority:** Required · **Depends on:** WP-29, WP-12  
**Requirements:** CAT-02, PR-04, AS-01

**Implement:** Select subset/all/none, filter, add guest with valid part, copy member regular assignment into saved participant default, explicit refresh action.

**Acceptance / tests:** Existing project unchanged after member master edit; selected subset persisted, guest no permanent member addition; defaults and overrides separate.

### WP-34 — Ensemble roles and explicit mapping editor

**Complexity:** M · **Priority:** Required · **Depends on:** WP-29, WP-31, WP-11  
**Requirements:** CAT-04, AS-07

**Implement:** Project-scoped roles and mapping CRUD: role × instrument variant, project default and position exception. Validated compatible playable parts, no automatic transposition.

**Acceptance / tests:** Four-role/seven-person fixture with role 3 on trombone and tenorhorn using distinct notation; missing mapping visible; same number not sufficient.

### WP-35 — Replacement and edition preference rules

**Complexity:** M · **Priority:** Required · **Depends on:** WP-29, WP-23a  
**Requirements:** CAT-03, AS-05–06

**Implement:** Global/project/position replacement rule CRUD and project/position edition preferences, validate scope, part/edition consistency and one-hop policy/cycles.

**Acceptance / tests:** Specificity, invalid cross-project mappings, cycles, incompatible/unconfirmed versions rejected; manual choices protected.

### WP-32 — Central assignment and edition resolver

**Complexity:** M · **Priority:** Required · **Depends on:** WP-31, WP-34, WP-35, WP-23a  
**Requirements:** GR-09–10, AS-01, AS-05–07

**Implement:** Pure service returning desired/effective part, exact confirmed version, provenance, missing and warnings; saved default/role/personal precedence, explicit/preferred/sole edition, fallback only if unavailable.

**Acceptance / tests:** Resolution priority matrix, manual Posaune 2 when 3 exists, same role different instrument, preferred vs explicit version, missing/ambiguity and invalid override behavior; no unconfirmed input.

### WP-33a — Matrix view and effective provenance

**Complexity:** M · **Priority:** Required · **Depends on:** WP-30, WP-32  
**Requirements:** AS-02, AS-08

**Implement:** Render shared positions × selected people, headers, saved defaults, actual part and edition provenance, missing/ambiguity/substitution, reserved non-editable cells.

**Acceptance / tests:** Mathias/Sebi/Riccardo fixture correct; labels and reserve behavior; same resolver as preflight later.

### WP-33b — Direct matrix cell and default edits

**Complexity:** M · **Priority:** Required · **Depends on:** WP-33a  
**Requirements:** AS-03, AS-08

**Implement:** HTMX direct dropdown edits with confirmed alternatives, key/clef and edition, project revision guard, default in header, clear errors; persist exact selection.

**Acceptance / tests:** Change only Riccardo at selected piece, including compatible notation; other cells/master/RAW unchanged; reload persists; stale edit rejected.

### WP-33c — Batch edits and explicit reset

**Complexity:** S · **Priority:** Required · **Depends on:** WP-33b  
**Requirements:** AS-04, AS-08

**Implement:** Select multiple cells for one participant; validate batch, apply transaction, reset selected overrides, retain explicit overrides on default change.

**Acceptance / tests:** Invalid batch has clear result and no partial unintended edits; reset one cell only; multi-edit and reload; no list/number mutations.

### WP-33d — Matrix filters and performance

**Complexity:** M · **Priority:** Required · **Depends on:** WP-33c  
**Requirements:** AS-02, AS-04, UI-03

**Implement:** Fixed headers, participant/instrument/deviation filters, prefetch/cached availability, incremental updates, optional lazy/paged rows.

**Acceptance / tests:** Browser usability with 100×50 synthetic matrix; measure query counts and response, no N+1 growth per cell; report actual limits.

### WP-36a — Preflight and missing-note report

**Complexity:** M · **Priority:** Required · **Depends on:** WP-33c, WP-32  
**Requirements:** GR-09, EX-08

**Implement:** Report chosen participants/positions, missing, substitutions, ambiguous editions, unreviewed candidates, overrides/layout flags; corrections and explicit acknowledgement UI.

**Acceptance / tests:** Missing report visible and blocking until acknowledgment; corrupt inputs actionable; no unconfirmed note used; report values match matrix.

### WP-36b — Immutable snapshot and generation authorization

**Complexity:** M · **Priority:** Required · **Depends on:** WP-36a, WP-05b, WP-29  
**Requirements:** GR-15, EX-09

**Implement:** Canonical snapshot fingerprint, relational pinned input versions, preflight validity/ack binding, atomic enqueue and run model; ensure relevant changes invalidate preflight before enqueue.

**Acceptance / tests:** Server rejects bypass/stale confirmation; edit during queued/running job does not change snapshot; pinned inputs protected; different participant outputs share same position sequence.

### WP-37a — PDF composition primitives and German contents

**Complexity:** M · **Priority:** Required · **Depends on:** WP-17, WP-36b  
**Requirements:** EX-05, EX-07, GR-12

**Implement:** Shared PDF builder, generated contents without page numbers, optional cover, German missing placeholders, Unicode fonts, no note overlay, preserve page size and vector where possible.

**Acceptance / tests:** Structural tests: reserve numbers appear only in contents, native A3 intact, cover optional, contents pagination, placeholder per missing position; no new marks on music.

### WP-37b — Personal full-folder generation

**Complexity:** M · **Priority:** Required · **Depends on:** WP-37a, WP-36b  
**Requirements:** EX-01, EX-09, GR-07–08

**Implement:** Worker builds one personal reading artifact per selected participant from snapshot, staged publication and manifest; no full part-only mode.

**Acceptance / tests:** Same shared list/numbering for all, different assigned parts, missing acknowledged placeholder, generation abort no falsely complete result; old file immutable.

### WP-37c — Project excerpts and contents-only export

**Complexity:** M · **Priority:** Required · **Depends on:** WP-37b  
**Requirements:** EX-02, EX-04, EX-06

**Implement:** Select positions/people from project or matrix, use same resolver/snapshot builder, no default cover/TOC for excerpt; separate full contents-only download. Include replacement-at-slot and historical exact reprint workflows.

**Acceptance / tests:** Lost ABBA Medley for Riccardo uses assigned Posaune 2; multiple positions/people, no list changes; separate updated contents; no full regeneration required.

### WP-38a — Regular print layout planner

**Complexity:** M · **Priority:** Required · **Depends on:** WP-37a  
**Requirements:** GR-11, PT-01–02, EX-07

**Implement:** Pure media planner for arbitrary consecutive A4 portrait runs, A3 whole, odd page, mixed/custom boundaries; no pairing with generated pages or across positions.

**Acceptance / tests:** 1–6 and >6 pages, duplicate arrangement separate positions, native A3 mixed with A4, rotated/landscape cases, no cross-boundary pairing. Structural tests verify exact media sizes.

### WP-38b — Print PDF renderer and manifest

**Complexity:** M · **Priority:** Required · **Depends on:** WP-38a, WP-37c, WP-23b  
**Requirements:** EX-07, PT-01–02

**Implement:** Render planner to print artifacts for full/excerpt/archive/contents, correct left/right transforms, printable content checks; display preview. Keep reading artifacts independent.

**Acceptance / tests:** Page geometry, visual fixtures and reading order verified; no clipping or splitting native A3; downloadable print output works without printer.

### WP-39 — Export library, targeted regeneration and stale status

**Complexity:** M · **Priority:** Required · **Depends on:** WP-37c, WP-38b, WP-36b  
**Requirements:** EX-10, GR-15, AR-17, EX-03

**Implement:** Unified run/artifact list, authenticated download, manifests and per-person paths, targeted regeneration, stale reasons for relevant project/catalog/preference changes, protected history. Integrate direct archive export with shared artifact model, including immutable archive-note snapshots for generated multi-note PDFs (no project required). Keep direct downloads of existing confirmed PDFs available.

**Acceptance / tests:** Part change marks affected output stale, old bytes unchanged, new single-person run succeeds, archived version pinned; no failed/partial artifact exposed as complete.

## M4 — Scan enhancement and marchbook

### WP-40a — Scan enhancement framework and deskew

**Complexity:** M · **Priority:** Required · **Depends on:** WP-17, WP-24  
**Requirements:** SC-01, SC-02

**Implement:** Pure per-page processing API, staff-line angle estimate, bounded deskew and confidence/skip, before-after fixtures.

**Acceptance / tests:** Known synthetic skew corrected within measured tolerance; no cropping musical marks; unsure angle warns; RAW/CLEAN untouched.

### WP-40b — Noise and shadow reduction

**Complexity:** M · **Priority:** Required · **Depends on:** WP-40a  
**Requirements:** SC-02

**Implement:** Conservative independent noise and shadow stages with configurable parameters, disable by default if risky; benchmark.

**Acceptance / tests:** Synthetic staff lines, accidentals and dynamics remain visible; no destructive default threshold; compare before/after.

### WP-40c — Safe crop and normalization

**Complexity:** M · **Priority:** Required · **Depends on:** WP-40a  
**Requirements:** SC-02, SC-03

**Implement:** Margin detection with padding and confidence; aspect-preserving page fit; exact physical dimensions where requested; flag questionable crop.

**Acceptance / tests:** Edge-note fixture preserved; crop opt-out; no distortion; page format tests and safe fallback.

### WP-41 — Scan enhancement UI and derivatives

**Complexity:** M · **Priority:** Required · **Depends on:** WP-40a, WP-40b, WP-40c, WP-20a, WP-23a  
**Requirements:** SC-01–02, AR-17

**Implement:** Separate processing UI, parameter/profile settings, preview, worker job, derivative lineage/hash, review before availability; choose approved derivative as preferred or explicit edition.

**Acceptance / tests:** Base hash unchanged, derivative separate, visual approval required, restart/retry safe, preferred selection works.

### WP-42 — Marchbook project and print layout

**Complexity:** M · **Priority:** Required · **Depends on:** WP-38b, WP-41  
**Requirements:** SC-03, GR-12

**Implement:** Add configurable landscape marchbook layout default 170×120 mm, aspect-ratio fit, cover/contents, original-format reading PDF, actual-size print manifest.

**Acceptance / tests:** Exact dimensions within tolerance, no overlay/crop, common numbering, native reading page preserved, print preview with margins.

### WP-40f — Private visual quality acceptance

**Complexity:** S · **Priority:** Required · **Depends on:** WP-41, WP-42, WP-22  
**Requirements:** SC-02, OP-02

**Implement:** Compare representative real scans privately on authorized NAS, assess notation preservation, speed/memory and manual controls; document aggregate results only.

**Acceptance / tests:** Archivist acceptance or explicit limitations; synthetic tests not misrepresented as real scan validation.

### WP-43 — Optional numbered part-folder adapter

**Complexity:** M · **Priority:** Optional · **Depends on:** WP-15, WP-30, WP-27  
**Requirements:** SC-04

**Implement:** Index `part/number_title.pdf`, propose shared positions and conflicts, require review and confirmation; no separate folder mode.

**Acceptance / tests:** Conflicting title/number cases require decision; same copy/review invariants; no independent participant list.

## M5 — Verified printer integration

### WP-44b — Printer adapter and capability settings

**Complexity:** M · **Priority:** Required · **Depends on:** WP-44a, WP-05b, WP-38b  
**Requirements:** PT-03, OP-03

**Implement:** Implement verified IPP/CUPS adapter, internal endpoint allowlist, configurable printer list, media/tray/capability display, PRINT_ENABLED default off.

**Acceptance / tests:** Mock capabilities, internal network allowlist, disabled path rejected; actual printer verification documented separately.

### WP-45 — Print preview, submission and status

**Complexity:** M · **Priority:** Required · **Depends on:** WP-44b, WP-38b, WP-39  
**Requirements:** PT-03, PT-05

**Implement:** Preview selected artifacts and copy count, persist submission intent and spool IDs, ordered mixed-media or contiguous blocks, cancellation and unknown-status workflow.

**Acceptance / tests:** Mock order and partial submission; crash/timeout after possible acceptance => UNKNOWN without retry; all output types supported; actual print test only with approval.

### WP-46 — Explicit A4 fallback and custom media

**Complexity:** M · **Priority:** Required · **Depends on:** WP-45, WP-42  
**Requirements:** PT-02–04

**Implement:** Fallback preview: unpair generated A3 spreads or scale native A3 whole, no split, explicit acknowledgement; marchbook media support/alternate; finalize safe landscape handling.

**Acceptance / tests:** A3 unsupported requires confirmation, native A3 unsplit, reading PDF unchanged; physical paper/actual scale and output order verified on authorized printer.

## M6 — Operations, validation and release

### WP-47b — Complete backup/restore and retention

**Complexity:** M · **Priority:** Required · **Depends on:** WP-47a, WP-39, WP-41  
**Requirements:** OP-05

**Implement:** Extend consistent snapshot to all retained archive versions/derivatives, manifests/config/secrets and selected exports; documented Hyper Backup integration, isolated restore and retention protections.

**Acceptance / tests:** Restore complete synthetic workflow, actual files and DB hashes verified; live archive unaffected; verify backup destination and restore process privately.

### WP-48 — Installation and operator runbooks

**Complexity:** M · **Priority:** Required · **Depends on:** WP-22, WP-47a, WP-07  
**Requirements:** OP-01, OP-03, OP-05

**Implement:** Write docs/INSTALL.md, UPDATE.md, DEBUG_MODE.md, RESTORE.md and German archivist guide. Include actual DSM steps, service UID/GID ACL, reverse proxy, migrations, GHCR pull, mode, troubleshooting.

**Acceptance / tests:** Runbooks validated against authorized deployment; no real paths/IDs/secrets leaked; separate example vs actual private config.

### WP-49 — Controlled update and rollback rehearsal

**Complexity:** M · **Priority:** Required · **Depends on:** WP-47b, WP-48, WP-10  
**Requirements:** OP-05, OP-06

**Implement:** Stop/quiesce both services; backup DB and files, pull exact approved tag, migrate once, smoke test; rollback with compatible DB/file state or restore.

**Acceptance / tests:** Test two versions with migration and changed file layout; verify old state restored; explain post-backup loss risk. No automatic production deploy.

### WP-50 — Final security and RAW audit

**Complexity:** M · **Priority:** Required · **Depends on:** WP-46, WP-47b, WP-33d, WP-04b  
**Requirements:** GR-01, GR-13–14, OP-03, OP-04

**Implement:** Audit business routes, IDOR/CSRF, PDF actions, path/ACL negatives, non-root mounts, logs, secrets, dependency/image scans, network allowlist; repeat RAW protection for all workflows.

**Acceptance / tests:** No unresolved high/critical issues without explicit risk decision; synthetic audit report; no weakening tests; actual NAS rights verified.

### WP-51 — Final license and dependency inventory

**Complexity:** S · **Priority:** Required · **Depends on:** WP-10, WP-46, WP-41  
**Requirements:** OP-06

**Implement:** Verify actual pinned Python/native/system/JS/font licenses and notices, transitive inventory and SBOM; correct uncertain license metadata; owner license decision.

**Acceptance / tests:** All shipped dependencies accounted for; notices distributed as required, no invented claims; dependency versions supported and verified.

### WP-52 — NAS load and SQLite verification

**Complexity:** M · **Priority:** Required · **Depends on:** WP-28, WP-39, WP-40f, WP-22  
**Requirements:** OP-02

**Implement:** Measure memory/CPU/I/O, queue recovery, WAL/busy timeout, 100×50 matrix, larger index and generation, scratch quota and service responsiveness. Tune actual defaults.

**Acceptance / tests:** Record hardware and measurements, no unexplained OOM/DB lock failures in agreed workload; limitations documented; not a guaranteed performance SLA.

### WP-53 — Full acceptance and approved release

**Complexity:** M · **Priority:** Required · **Depends on:** WP-46, WP-47b, WP-48, WP-49, WP-50, WP-51, WP-52  
**Requirements:** All required IDs

**Implement:** Trace all requirements to work/tests; full workflow privately on NAS from copy/review to project, excerpt, marchbook and print; record blockers and actual implemented scope. Recommend version, commit/PR/tag, GHCR publish and manual deployment for approval.

**Acceptance / tests:** All required full-scope gates evidenced or explicitly excluded from a separately approved limited release; acceptance report, release notes, artifact digest, rollback point. Optional WP-43 not a blocker.

## 3. WP-01 — immediate implementation checklist

**Objective:** Establish a small, reproducible, testable foundation. Do not create full application features in this package. The current repo is not assumed empty or clean.

1. Verify workspace and active branch (`git rev-parse --show-toplevel`, `git status --short --branch`, `git diff`). Read these six documents. Preserve existing user edits; if an existing branch is intended for setup, use it with owner agreement instead of silently deleting or changing branches.
2. Confirm Python 3.12 and uv availability. Check foundation package compatibility (Django 5.2 LTS, Ruff, pytest); choose pinned supported versions. Use `requires-python = ">=3.12,<3.13"` for this baseline; add other dependencies when their package begins. Use `uv.lock` and `uv sync --locked`. Do not download unrelated software or use actual archive data.
3. Create `pyproject.toml` with runtime/dev groups, Ruff target py312 and practical line length (e.g. 120), pytest testpaths. Create a meaningful smoke test verifying configured foundation/imports; avoid meaningless assertions. Add pytest-django when Django tests need it. Include a synthetic fixture policy and test folder.
4. Create `.gitignore` and `.dockerignore` for caches, virtualenv, secrets, real archive exports/DBs/logs, local `.env`, scratch and build artifacts; allow explicitly generated synthetic fixtures. Ensure tracked docs are included. Establish a dependency-license inventory mechanism (actual metadata, not guesses); do not create a definitive LICENSE unless the owner has approved license/copyright information.
5. Add `.github/workflows/ci.yml` with least-privilege permissions, approved/pinned actions, locked sync, Ruff lint/format and pytest; no production credentials. Additional Docker/browser/security steps belong to their packages. The CI workflow is not proven green until actually run.
6. Run `uv lock --check`, `uv sync --locked`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest`. Review changed files and diff. Report exact outcomes, remaining unverified CI and dependency issues. Update README development commands if changed.
7. Recommend a commit such as `chore: bootstrap development tooling and CI` and next package WP-02. Request approval to commit/push/PR as appropriate; after approval execute without repeated confirmation. Do not start WP-02 until authorized.

**Acceptance:** Fresh checkout with supported interpreter can sync locked environment, pass lint/format/tests and run CI definition. No secret/real-data artifacts, no speculative app code and no changes to binding requirements. A missing tool or unavailable CI must be reported, not hidden. Suggested branch `feature/wp-01-project-foundation` if no owner-designated setup branch exists.

## 4. Test strategy and traceability

Tests use deterministic synthetic PDF/scan fixtures created with ReportLab/Pillow or comparable tools; no actual association files or member records. Real visual quality, NAS permissions, printer behavior and resource validation are separate owner-authorized checks. Do not conflate test coverage with musical accuracy. Build a `tests/TRACEABILITY.md` mapping individual requirement IDs to actual test names as packages are completed; this table is the planned minimum, not evidence of tests already passing.

| Business invariant | Planned verification | Work packages |
| --- | --- | --- |
| GR-01 RAW never written | Synthetic host ACL + mount negative write/rename/delete; before/after hash inventory through index, correction, enhancement/export | WP-09, WP-22, WP-14, WP-15, WP-41, WP-50 |
| GR-02 Real identical copies | Hash comparison, pre-existing destination conflict, crash and copy stability | WP-14, WP-15 |
| GR-03 Actual content checked | Filename/content disagreement, scanned clear name, text/region/OCR evidence | WP-19, WP-20a, WP-24, WP-25 |
| GR-04 Manual inspection | Uninspected/stale-version batch rejected, approval/publish failure, combined assignments | WP-20a, WP-20b, WP-26 |
| GR-05 Independent statuses | Pending/confirmed vs missing/unknown expectation; marker state | WP-13, WP-16, WP-21 |
| GR-06 Changed versions and reuse | Same hash skips routine reprocessing, changed version review, same-mtime integrity, removed source preserved | WP-27 |
| GR-07 Common list | Automatic numbering, reserve slots, repeats, replacement at same position; full-folder sequences identical | WP-30, WP-37b |
| GR-08 Personal full folders | Project excerpt, archive direct export, contents-only, no part-only full mode | WP-23b, WP-37b, WP-37c |
| GR-09 Missing notes | Server ack required; placeholder, no silent omission or unconfirmed substitute | WP-32, WP-36a, WP-36b, WP-37a |
| GR-10 Assignment priority | Saved default snapshot, manual Posaune 2, ensemble roles, explicit version, replacement, reset and batch | WP-31, WP-34, WP-35, WP-32, WP-33b, WP-33c |
| GR-11 Sheet layout | A3 uncut, arbitrary A4 count, no cross-position pairing, mixed sizes/fallback | WP-38a, WP-38b, WP-46 |
| GR-12 No page stamping | Render/structure comparisons for all normal and marchbook note pages; contents only numbered | WP-37a, WP-42 |
| GR-13 Debug safety | Absent/TRUE/FALSE/invalid values, gated authenticated GUI, rotation, restart, no Django DEBUG | WP-02, WP-04a, WP-04b, WP-07 |
| GR-14 Privacy/local | Offline startup/local assets, log sanitization, secret/fixture scans, safe authorized real validation | WP-08, WP-18, WP-24, WP-50 |
| GR-15 Immutable outputs | Invalidated report after edits, job uses pinned versions, old artifact bytes unchanged, stale marking | WP-36b, WP-37b, WP-39 |

Test layers: unit tests for naming/safety/matching/format/layout/resolver and status transitions; integration tests with real file-backed SQLite connections for concurrency, atomic claims, constraints, fencing, snapshots and file intents; PDF structural and golden visual tests; Playwright workflow tests for review, drag-and-drop, matrix and exports; container smoke tests with synthetic bind mounts and non-root identity; security negative tests, resource benchmarks, actual NAS and printer acceptance; isolated restore and update/rollback rehearsal. For printer, use mocks in CI and actual physical output checks on-site. Do not automatically retry a print in a test recovery scenario.

## 5. Cross-phase risk and release gates

| Risk | Mitigation / gate |
| --- | --- |
| Irreplaceable archive damage | Strict dual RAW read-only, independent backup, no physical RAW marker, safe copy/publish and recovery; test synthetic roots before real use. |
| Wrong playable part | Mandatory visual confirmation, explicit key/clef, shared resolver, no guessing from matching number; missing/ambiguous state. |
| OCR or scan filter damages notation / poor recognition | Manual workflow first, local benchmarks, conservative processing, preview and human quality acceptance. |
| SQLite contention or worker crash | Local storage, short transactions, bounded retries, conditional claim and singleton lease, fencing and durable file intents; no exactly-once promise. |
| 2 GB RAM | Single heavy worker, bounded subprocesses/pages/scratch, actual NAS measurements, adjust limits or add RAM if owner approves. |
| Printer capabilities unknown | Early discovery, PDFs independent of printing, feature flag, explicit fallback and no automatic retry. |
| Version changes and approval race | Immutable snapshots with pinned inputs, revalidate preflight before enqueue, preserve historical output. |
| Scope creep and agent confusion | Stable IDs and explicit source authority; small work packages and approvals; pending hardware evidence blocks only related gate. |

**Before real-data use:** verify dual RAW protection, backup/restore, authorized storage roots, authentication, private network and local resource limits. **Before MVP acceptance:** complete M0/M1 and relevant M2 recognition, M3 personal-folder, ensemble, snapshot, excerpt and regular print-PDF tests; describe any absent features. **Before full release:** all required M4–M6 checks including actual printer, marchbook and scan acceptance, restored complete state, validated dependency/license notices, security and regression. Optional WP-43 may remain pending. If any hardware or dependency verification is unavailable, record it and obtain explicit limited-release approval; never claim full acceptance by extrapolating from mocks.

## 6. Progress record

Maintain a concise status record as actual work progresses (may be a separate `docs/PROGRESS.md` later): WP ID, approved scope, status, commit/PR, test evidence, blockers and next recommendation. All WPs are **Planned** at this specification revision. No Git change, dependency installation, application execution, NAS operation or deployment is implied by this plan.
