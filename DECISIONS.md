# Decisions and validation register

**Revision:** 2.0 — 2026-11-19

This register distinguishes binding product decisions from recommended implementation defaults and facts that require actual verification. It is not a new round of general planning. WP-01 can begin after the owner accepts the baseline and authorizes implementation; later questions block only the relevant feature. Record new decisions with a date, rationale, scope and affected requirement IDs. Do not silently promote an assumption to a product rule.

## Confirmed product decisions

| ID | Decision | Requirements |
| --- | --- | --- |
| DEC-01 | Independent local application; RAW is never modified; byte-identical physical CLEAN copies; separate STATUS marking; manual visual review even for clearly named files. | GR-01–06, AR-01–14 |
| DEC-02 | One common list; complete folders only per person; individual excerpts and independent archive-note exports are allowed; no personal additions or omissions; no numbers printed on music. | GR-07–08, GR-12, PR-01–06, EX-01–06 |
| DEC-03 | Automatically renumber upon order changes; explicit empty positions consume numbers and only appear in contents. | PR-03 |
| DEC-04 | Project-specific and per-position personal assignments; direct matrix editing, batch edits, reset; select confirmed notation/key editions; archive preferred version with explicit overrides. | AS-01–08, AR-17 |
| DEC-05 | Small ensembles map musical roles to playable instrument parts; no automatic transposition. | CAT-04, AS-07 |
| DEC-06 | Native A3 stays whole; pair A4 portrait only within a piece; regular reading order; A4 fallback only after approval; marchbook default 170 × 120 mm. | GR-11, PT-01–05, SC-03 |
| DEC-07 | Deploy default; optional `DEBUG_MODE="TRUE"` enables application GUI and file diagnostics, never Django DEBUG. | OP-04 |
| DEC-08 | All development instructions/docs English; GUI and archivist manuals German. Owner update 2026-11-20: routine commits, pushes, PRs and merges within agreed implementation scope proceed without repeated approval after successful relevant checks/CI and diff review, with no unresolved errors, review findings or conflicts. Blocking decisions and actions beyond this scope retain their approval requirements. | UI-02, OP-06, AGENTS.md |
| DEC-09 | Owner priority shift 2026-11-20: first deliver an empty/synthetic-data web-only technical preview on DS224+. Advance deployment-compatible WP-09/06/07/08/10 and preview backup/install/rollback slices of WP-47a/48/49. Worker recovery, OCR, printing and generation do not block this web-only variant; their original requirements and full-scope dependencies remain. Actual GHCR release/tag and NAS deployment retain their applicable approval gates; no real archive attachment or live NAS deployment is authorized. | OP-01–06, UI-01–03, GR-01/13/14; IMPLEMENTATION_PLAN.md preview gate |

## Recommended defaults for owner acceptance

These defaults are used to make the plan concrete. They are reversible design choices, not new confirmed requirements. The owner can adjust them without another full review.

| ID | Default / rationale | Verify or revisit by |
| --- | --- | --- |
| D-01 | Python 3.12 + Django 5.2 LTS, uv, Django templates/HTMX, SQLite, one durable worker, same image. Lean architecture for DS224+. | WP-01 / WP-02 compatibility checks |
| D-02 | Human-readable piece/arrangement folders; no unconditional UUID suffix; part filename includes relevant key and clef. Prefer separate PROCESSED root to distinguish derivatives. | WP-14 |
| D-03 | Reserves are explicit ordered slots; insertion/drag-and-drop updates numbers of all slots. A reserve can be moved, filled or deleted deliberately. Filling/replacing a slot keeps its position ID; changing order can shift reserve numbers. Show preview, do not lock reserve number labels by default. | WP-30 (confirm interaction with owner) |
| D-04 | Expected-part list per arrangement with reusable templates. No list = unknown completeness. | WP-11 / WP-21 |
| D-05 | Save project default on participant addition; explicit refresh of member default only. Ensemble mapping by position and instrument variant; no number-based fallback. | WP-31 / WP-34 |
| D-06 | Preferred edition precedence: exact personal selection, position preference, project preference, archive preference, sole suitable confirmed version. Ambiguous alternatives require a choice. One-hop substitution, position > project > global. | WP-32 / WP-35 |
| D-07 | Export structure by project/person/run, separate reading and print artifacts; contents-only and archive notes independently; retain old referenced versions and outputs, no automatic destructive cleanup. | WP-39; retention details before production |
| D-08 | Excerpts and direct notes without cover/TOC by default; separate contents-only export; a batch may offer ZIP or explicitly combined archive-note PDF. | WP-23b / WP-37c |
| D-09 | Single-sided regular printing; leave A4 landscape/custom pages safe and whole pending preview and explicit layout decision. Native A3 scaled whole for fallback; A3 made from A4 may unpair to original A4. | WP-38a / WP-46 |
| D-10 | Feature branches from main; CI progressively added; no deletion of existing branches automatically. Private repo and provisional all-rights-reserved license only if owner approves; do not invent copyright owner or assume redistribution rights. | WP-01; owner approves license before adding LICENSE |
| D-11 | Manual indexing by default; optional later schedule. Optional numbered voice-folder adapter after MVP. | WP-43 |
| D-12 | M3 is useful personal-folder MVP, not a claim of full feature completion. Full product release includes OCR, ensemble, marchbook, printing and operations; if hardware blocks printing, release only explicitly limited scope with owner approval. | WP-53 |
| D-13 | Minimal common navigation early; use synthetic UI acceptance fixtures and the German mockup as an interaction reference, not as production code or normative behavior. | WP-03a |
| D-14 | 10 MiB/5 backups per writer, one writer per log file. Deploy preserves existing debug files; no debug GUI. | WP-04a / WP-04b |

## Hardware and evidence still outstanding

| ID | Required evidence | Deadline / impact |
| --- | --- | --- |
| V-01 | Actual DSM/Container Manager version, NAS CPU/RAM availability, configured shares, filesystem and service UID/GID/ACL; host bind source and mount verification. | WP-22; blocks real NAS use, not local coding. |
| V-02 | Dependency compatibility, exact locked versions, license notices, supported amd64 native packages. | WP-01 for selected foundation, repeat whenever added; final WP-51. |
| V-03 | Real internal printer endpoint(s), media/tray capabilities, printable margins, mixed-format order, actual-size marchbook support and status behavior. | Early WP-44a; blocks live print, not PDF output. |
| V-04 | OCR and scan enhancement quality on representative real music locally, memory/time measurements. No real scans sent to CI or remote models. | WP-28 / WP-40f; synthetic fixtures alone not sufficient for production quality claims. |
| V-05 | SQLite filesystem/WAL and actual load, job recovery behavior, local permission boundary. | WP-22 and WP-52. |
| V-06 | Owner preference on exact cover/contents design, treatment of unusual formats, retention policy and historical print workflow. | Relevant UI/export/print package; not WP-01 blocker. |
| V-07 | Actual GitHub plan/branch protection and GHCR permissions; registry package name, credentials, desired license/copyright holder. | WP-01/08/10; no unapproved repository administration. |
| V-08 | NAS backup destination, retention and tested restoration, consistent maintenance boundary. | WP-47a before real archive data; WP-47b final test. |

Do not pretend the repository, NAS, printer, dependency environment or runtime has been inspected when only specification files are available. Record actual outcomes in the relevant runbook and update this register when evidence exists.
