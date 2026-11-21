# Dependency-aware delivery sequence

Owner priority shift: 2026-11-20 (DEC-09). Stable WP identifiers and original
full-scope dependencies are preserved. This document counts packages, not
commits or estimated effort; a partial package is still unfinished.

Owner extension 2026-11-21: finish current WP-11/12 (WP-05b/05c is merged), then
WP-17, then separate feature/synology-simple-install with standalone configuration.yaml
and a concise German guide. Each starts from verified main and integrates fully
before advancing. Afterwards select a bounded, dependency-ready manual archive
slice when it can be completed and tested; the earlier stop after WP-17 is revoked.
Do not infer authorization for additional releases, real data or NAS deployment.
The independent lanes below are coordination guidance, not dispatched agents.

## Counts and preview boundary

- Total: **71 packages**, including optional WP-43; **70 required**.
- Baseline after WP-05a integration: **7 fully software-verified and merged**;
  **64 unfinished**, including partial and optional work. NAS acceptance is
  tracked separately and is not inferred from CI.
- Preview work touches **8 further existing WP IDs**: five deployment IDs
  (WP-09/06/07/08/10) plus three early safety/operator slices
  (WP-47a/48/49). No extra administrative WPs are invented.
- Current published preview: **10 complete, 61 unfinished** (60 required plus
  optional WP-43). WP-09/08 integrated through PR #8 and WP-10 is verified by
  approved `v0.1.0-preview.1` publication. See [release evidence](RELEASES.md).
- Current source after verified WP-05b/05c acceptance: **12 complete, 59 unfinished**
  (58 required plus optional WP-43); CI `44823399459`, PR #11. The published
  preview image is unchanged; PR #11 merged at 470e7c8 with main CI 44824237705.
- Current source after WP-11/12 acceptance: **14 complete, 57 unfinished**
  (56 required plus optional WP-43); PR #12, full CI 44841036938. Verify its
  final merge/main CI before starting WP-17.
- WP-06/07 and WP-47a/48/49 are deliberately partial against the full
  application. The software preview publication gates are complete.
- No further package blocks pulling the published preview. Installation on
  the actual NAS still needs the separately
  approved WP-22 preview check; full WP-22 also validates the later worker/UI.

The first installation is an authenticated technical preview with honest
placeholders, not archive ingestion or the full product. Existing WP-03a's
Playwright DB fix is integrated in PR #4; WP-04a's .dev clone is clean and
already included via PR #5. No implementation is duplicated from those clones.

## Delivery order and genuine dependencies

1. The preview image is published, pulled and attested at its exact GHCR digest.
   The next deployment step is separately authorized private DSM validation
   with new synthetic roots (WP-22 slice); no live NAS deployment has occurred.
2. In parallel, build WP-05b→05c (durable recovery/cancellation/UI), WP-11→12
   (musical/member master data), and WP-17 (pure PDF foundation). These start
   from already satisfied foundations and do not depend on OCR/printing.
3. Deliver the manual archive vertical slice: WP-13→14 plus WP-17→19;
   integrate WP-15→16, WP-18→20a, then WP-20b/21→23a→23b. Complete full
   WP-47a and the RAW/NAS gate before real ingestion. Publication requires
   WP-05b; visual confirmation cannot be skipped for a faster release.
4. Start projects (WP-29) once WP-11/12/13 exist, independently of OCR quality.
   Then WP-30/31, WP-34/35, central resolver WP-32, matrix WP-33a–33d,
   preflight/snapshots WP-36a/b and generation WP-37a–37c. Keep immutable
   authorization/snapshot boundaries even when grouped into a PR.
5. In parallel with projects, deliver OCR WP-24→25→26/27→28. The OCR engine
   requires PDF/native foundations; recognition/review integration depends on
   actual index/review models. Hardware quality is a private NAS gate.
6. Integrate print-PDF layout WP-38a/b→39; scan enhancement WP-40a/b/c→41
   can run independently once WP-17/24 and archive approval exist. Marchbook
   WP-42 requires both layout and approved derivatives; private quality WP-40f
   remains required. Optional WP-43 can wait without blocking acceptance.
7. Printer capability WP-44a needs owner-approved hardware access; it need not
   block PDFs. Actual adapter WP-44b→45→46 requires verified media/layout and
   the no-automatic-retry operation contract. Never infer printer support.
8. Finish WP-47b/48/49, final security/license WP-50/51, actual NAS load WP-52
   and full acceptance WP-53. Early runbooks/scans are reused and extended;
   they do not replace these final gates.

## Useful grouping and independent agent lanes

| Group | Codex lane | OpenCode lane | Integration boundary |
| --- | --- | --- | --- |
| Immediate foundations | WP-05b/05c, worker/mutation contracts | WP-11/12 master data; WP-17 can be a separate pure-PDF branch | Freeze service IDs/payload contracts; separate migrations/apps |
| Manual archive | WP-13/14/15 backend and no-clobber publication | WP-18/20a UI after model/preview contracts; WP-16 alongside index API | One integration owner for URLs/base navigation; merge model/services first |
| Projects and recognition | WP-24/25 OCR and WP-27 integrity | WP-29/30/31 project UI; WP-34/35 rules after dependencies | Separate processing/catalog/project modules; synthetic fixtures only |
| Resolver and matrix | WP-32 resolver and WP-36b snapshot services | WP-33a–33d matrix against the single resolver | No duplicate resolution logic or premature generation endpoint |
| Output and scan | WP-37/38 output/layout services | WP-40a/b/c enhancement and WP-41 UI after prerequisites | Shared PDF APIs agreed first; exact hashes/approval retained |
| Operations | Container/release integration owner | Runbook/acceptance review and authorized private NAS evidence | Never run concurrent live migrations/deployments |

Use separate feature branches/worktrees from the same verified base. Do not
have both agents edit shared configuration, base templates, migration chains
or progress snapshots simultaneously; designate an integration owner and
merge dependent PRs in order. Communicate contracts and compare full diffs
from the recorded base on handoff. These are proposed independent lanes, not
claims that agents have been dispatched or unimplemented prerequisites exist.

## Complete package register

Current snapshot after approved preview publication run `44817372155`. Original dependency IDs below
apply to the full package; DEC-09 only scopes the documented early slices.

| WP | Scope | Full-scope dependencies | Verified status / remaining gate |
| --- | --- | --- | --- |
| WP-01 | Repository, development tooling and minimal CI | None | Verified and merged |
| WP-02 | Django skeleton and configuration | WP-01 | Verified and merged |
| WP-03 | Authentication and session baseline | WP-02 | Verified and merged |
| WP-03a | Early application shell and navigation | WP-03 | Verified and merged |
| WP-04a | Technical logging and mode contract | WP-02 | Verified and merged |
| WP-04b | Authenticated debug UI | WP-04a, WP-03a | Verified and merged |
| WP-05a | Durable queue, claim and singleton worker | WP-02 | Verified and merged |
| WP-05b | Job recovery, cancellation and operation contract | WP-05a | Software verified; CI 44823399459 / PR #11 |
| WP-05c | Job UI and progress | WP-05b, WP-03a | Software verified; real browser cancellation, CI 44823399459 / PR #11 |
| WP-09 | Service-aware mount and startup validation | WP-02, WP-04a | Software verified, CI 44797427059 / PR #8; NAS gate separate |
| WP-06 | Minimal hardened container image | WP-02, WP-03a, WP-04a, WP-05b, WP-09 | Web-image slice; full worker gate pending |
| WP-07 | Compose services and data roots | WP-06, WP-09 | Web/tools Compose slice; worker integration pending |
| WP-08 | Extended CI and container verification | WP-07, WP-03a | Software verified, CI 44797427059 / PR #8 |
| WP-10 | Versioned container release pipeline | WP-08 | Verified; v0.1.0-preview.1 published, pulled and attested; RELEASES.md |
| WP-22 | Early NAS synthetic smoke | WP-07, WP-08, WP-04b, WP-05c | Planned |
| WP-44a | Early printer capability spike (validation only) | WP-22 | Planned |
| WP-11 | Musical catalog and expected-parts CRUD | WP-02, WP-03a | Software verified; CI 44841036938 / PR #12, merge checkpoint in HANDOFF.md |
| WP-12 | Membership and regular assignments | WP-11 | Software verified with German UI; CI 44841036938 / PR #12 |
| WP-13 | Archive versions and state model | WP-11 | Planned |
| WP-14 | Safe file copy, naming and publication | WP-13, WP-05b | Planned |
| WP-17 | PDF processing foundation | WP-01 | Planned |
| WP-19 | Filename and text-layer recognition | WP-13, WP-17 | Planned |
| WP-15 | Indexing and separate STATUS publication | WP-14, WP-17, WP-19, WP-05c | Planned |
| WP-16 | Indexing UI | WP-15, WP-03a | Planned |
| WP-18 | Secure PDF preview | WP-17, WP-13, WP-03a | Planned |
| WP-20a | Individual review and publication | WP-15, WP-18, WP-19 | Planned |
| WP-20b | Efficient review and batch approval | WP-20a | Planned |
| WP-21 | Library search and completeness | WP-20a, WP-11 | Planned |
| WP-23a | Preferred archive editions | WP-20a, WP-21 | Planned |
| WP-23b | Direct archive note download | WP-23a, WP-18, WP-17, WP-05c | Planned |
| WP-47a | Initial consistent backup and restore safety | WP-15, WP-20a | Preview DB/config/secret backup slice; full archive gate pending |
| WP-24 | Bounded local OCR engine | WP-17, WP-06 | Planned |
| WP-25 | OCR job and rule integration | WP-24, WP-15, WP-19 | Planned |
| WP-26 | OCR evidence review UI | WP-25, WP-20b | Planned |
| WP-27 | Incremental reindex, integrity and version lifecycle | WP-15, WP-23a, WP-25 | Planned |
| WP-28 | OCR quality and NAS resource measurement | WP-25, WP-22 | Planned |
| WP-29 | Project model, revisions, CRUD and duplication | WP-11, WP-12, WP-13, WP-03a | Planned |
| WP-30 | Shared piece list and automatic numbering | WP-29, WP-21 | Planned |
| WP-31 | Participants and saved project defaults | WP-29, WP-12 | Planned |
| WP-34 | Ensemble roles and explicit mapping editor | WP-29, WP-31, WP-11 | Planned |
| WP-35 | Replacement and edition preference rules | WP-29, WP-23a | Planned |
| WP-32 | Central assignment and edition resolver | WP-31, WP-34, WP-35, WP-23a | Planned |
| WP-33a | Matrix view and effective provenance | WP-30, WP-32 | Planned |
| WP-33b | Direct matrix cell and default edits | WP-33a | Planned |
| WP-33c | Batch edits and explicit reset | WP-33b | Planned |
| WP-33d | Matrix filters and performance | WP-33c | Planned |
| WP-36a | Preflight and missing-note report | WP-33c, WP-32 | Planned |
| WP-36b | Immutable snapshot and generation authorization | WP-36a, WP-05b, WP-29 | Planned |
| WP-37a | PDF composition primitives and German contents | WP-17, WP-36b | Planned |
| WP-37b | Personal full-folder generation | WP-37a, WP-36b | Planned |
| WP-37c | Project excerpts and contents-only export | WP-37b | Planned |
| WP-38a | Regular print layout planner | WP-37a | Planned |
| WP-38b | Print PDF renderer and manifest | WP-38a, WP-37c, WP-23b | Planned |
| WP-39 | Export library, targeted regeneration and stale status | WP-37c, WP-38b, WP-36b | Planned |
| WP-40a | Scan enhancement framework and deskew | WP-17, WP-24 | Planned |
| WP-40b | Noise and shadow reduction | WP-40a | Planned |
| WP-40c | Safe crop and normalization | WP-40a | Planned |
| WP-41 | Scan enhancement UI and derivatives | WP-40a, WP-40b, WP-40c, WP-20a, WP-23a | Planned |
| WP-42 | Marchbook project and print layout | WP-38b, WP-41 | Planned |
| WP-40f | Private visual quality acceptance | WP-41, WP-42, WP-22 | Planned |
| WP-43 | Optional numbered part-folder adapter | WP-15, WP-30, WP-27 | Planned (optional) |
| WP-44b | Printer adapter and capability settings | WP-44a, WP-05b, WP-38b | Planned |
| WP-45 | Print preview, submission and status | WP-44b, WP-38b, WP-39 | Planned |
| WP-46 | Explicit A4 fallback and custom media | WP-45, WP-42 | Planned |
| WP-47b | Complete backup/restore and retention | WP-47a, WP-39, WP-41 | Planned |
| WP-48 | Installation and operator runbooks | WP-22, WP-47a, WP-07 | Preview runbooks; physical NAS validation pending |
| WP-49 | Controlled update and rollback rehearsal | WP-47b, WP-48, WP-10 | Preview isolated restore slice; full two-version rehearsal pending |
| WP-50 | Final security and RAW audit | WP-46, WP-47b, WP-33d, WP-04b | Planned |
| WP-51 | Final license and dependency inventory | WP-10, WP-46, WP-41 | Planned |
| WP-52 | NAS load and SQLite verification | WP-28, WP-39, WP-40f, WP-22 | Planned |
| WP-53 | Full acceptance and approved release | WP-46, WP-47b, WP-48, WP-49, WP-50, WP-51, WP-52 | Planned |
