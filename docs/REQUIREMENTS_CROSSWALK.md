# Source aliases, coverage and acceptance

This is a crosswalk into REQUIREMENTS.md revision 3 and IMPLEMENTATION_PLAN.md.
It is not an additional requirements authority. Source EXT/FUT/REF identifiers
remain aliases. Canonical requirement and WP identifiers are preserved.

Source supplied by the owner on 2026-11-25 is
Notenarchiv_Codex_Requirements_Integration.md, including the integration
instructions and complete Appendix A. SHA-256 is
`453eb3ee9eb928c2b6b7a89b950db91ba2ac8d07af956d629c19425782c5994b`.

Coverage is assessed against main `ca8647cfb04d26e3d61048e22e8885e6b5c460bb`,
verified by Main CI 45640472935. That evidence covers the pre-extension software
and portability increments. It does not verify newly specified acceptance.
The incomplete OCR prototype is not implementation evidence.

AR-02 now explicitly scopes piece/part naming to simple sources and routes
compound sources to AR-26. PR-01's former phrase "one project = one collection"
means the shared project list and is distinct from the new catalog Collection.
GR-11/PT-02 regular-mode restrictions remain the legacy contract; explicit
template-driven behavior is new scope under DEC-13. No source priority conflict
is hidden by renumbering or by claiming old acceptance for the expanded scope.

## Extension and future aliases

| Source alias | Canonical requirements | WPs | Coverage and acceptance |
| --- | --- | --- | --- |
| EXT-01 | GR-16, AR-20/21/26, OP-08 | WP-13/17 extensions, WP-54 | Changed/new. SourceVersion has page_info and ArchiveFile has one arrangement. No confirmed logical content model. Additive migration and old-output replay must pass. |
| EXT-02 | AR-25/26, CAT-05/06, EX-11/12 | WP-54/55/56, WP-37/39 extensions | New. 125-work booklet and independent collection selection require REF-11–14/17/18/34. |
| EXT-03 | CAT-05/06, EX-11 | WP-55, WP-32/37 extensions | New. Existing Work/Arrangement have no parent-movement model. Deutsche Messe and shared movements require REF-15/16. |
| EXT-04 | AR-19/20/22, SC-06 | WP-15/16/24/25 extensions, WP-56 | New segmentation. Existing file inventory/recognition is partial infrastructure. Pass REF-01–08 without automatic approval. |
| EXT-05 | AR-21, SC-05, AR-12/13 | WP-56, WP-20a/b/26 extensions | Partial. tests/test_review_ui.py and test_batch_review.py cover file review. New group/region editing, invalidation and source-context inspection are unverified. |
| EXT-06 | AR-08–11/25, SC-06, OP-02 | WP-24–28, WP-54/55 | Partial text-layer/alias recognition in tests/test_archive_recognition.py. Bounded multi-title/region OCR and exact cache identity are new acceptance. |
| EXT-07 | EX-07/11–13, PT-06/08 | WP-37a/38a/b/42 extensions | Partial regular geometry/composition in tests/test_print_layout.py and test_pdf_composition.py. New n-up and region transforms require REF-17–21/26/36. |
| EXT-08 | PT-07, EX-13 | WP-57, WP-38/42 extensions | New persistent user templates. Validate every applicable property and freeze historical revisions, including REF-28. |
| EXT-09 | PT-08/09, EX-14 | WP-42/45/46 extensions | Changed scope from regular-only/no booklet. Per-final-page parity, binding, duplex and cut/fold acceptance are new REF-21–26/35. |
| EXT-10 | PT-10, EX-08/13 | WP-36a/38b/45/46 extensions | Partial existing preflight and regular render preview. Region confirmation, exclusions and front/back geometry need new acceptance. |
| EXT-11 | GR-07/08/12/15, EX-06/11–14 | WP-32/36–39/45/46 extensions | Partial confirmed file resolver/snapshots/reprints. Region replay, shared-page policy and insertion parity require REF-29/30/34–36. |
| EXT-12 | AR-22/23, SC-02 | WP-56, WP-40d/41 | Partial exact hash safety. Basic blank/duplicate handling is core. Advanced quality/perceptual matching is secondary, REF-09/10/27 when delivered. |
| EXT-13 | AR-24, OP-02 | WP-59, WP-15/16 extensions | New secondary/should. Stable-write inbox, history and duplicate protection. Manual import must work with it disabled. |
| EXT-14 | CAT-07 | WP-58 | New secondary/should. Hierarchical locations, stock/condition, independent physical availability and reports. Lending deferred. |
| EXT-15 | CAT-06/08, AR-15/25 | WP-11/21 extensions, WP-55/60a | Partial title/alias/part filters. New metadata, collection/movement/location/typo/combined searches need distinct tests. |
| EXT-16 | PR-08, GR-07 | WP-29–35 extensions, WP-60b | Partial project duplication, ordering, ensemble, completeness and batches. Templates/grouped exports/estimates remain secondary acceptance. |
| EXT-17 | PR-09, EX-10/14 | WP-39 extensions, WP-60b | Partial revision/stale/targeted export behavior in tests/test_export_library.py. Explicit revision comparison and insertion impact are new. |
| EXT-18 | UI-05 | WP-18 extensions, WP-60c | Partial authenticated file preview in tests/test_preview.py. Region/movement/song-87 navigation is new secondary acceptance. |
| FUT-01 | AR-27 | WP-61a | Deferred. License/receipt/permission workflow requires later approval. |
| FUT-02 | AR-28 | WP-61b | Deferred. Mapped inventory import is independent of PDF ingestion. |
| FUT-03 | AR-29 | WP-61c | Deferred. Stable identities are existing foundations, not QR workflow coverage. |
| FUT-04 | EX-15 | WP-61d | Important deferred feature. Official capability study before API/import assumptions. Existing individual PDFs/UUIDs do not establish interoperability. |
| FUT-05 | CAT-09 | WP-61e | Deferred. Physical lending/return requires separate specification. |
| FUT-06 | SC-07 | WP-61f | Deferred. Scanner/phone acquisition is not required for manual scan ingestion. |
| FUT-07 | UI-06 | WP-61g | Deferred. Tablet/offline/setlists/annotations/synchronized turns require later scope. |

## Reference scenarios and measurable oracles

Every REF alias is retained. A planned oracle is not a passing test. Existing
evidence is limited to the indicated simple workflow. New content/migration/
geometry integration fixtures must be added beside the existing suites.
All fixtures committed or sent to CI are synthetic deterministic documents.
Authorized realistic music stays private for separate quality/hardware acceptance.

| Source alias and scenario | Canonical requirements / WPs | Coverage and required oracle |
| --- | --- | --- |
| REF-01 large multi-part scan | AR-19, SC-06 / WP-24/25/56 | New. Compare proposed ordered part spans against fixture truth, including the 1–3/4–5/6–8/blank-9/10–11 example. |
| REF-02 three-page part | AR-19/20 / WP-54/56 | New. Exactly one part group retains all three pages in order. |
| REF-03 heading-free continuation | AR-19, SC-06 / WP-24/56 | New. Absence of repeated title/instrument alone does not create a group boundary. |
| REF-04 genuine A3 | GR-11, AR-20 / WP-17/38a/56 | Partial. tests/test_pdf.py and test_print_layout.py verify native geometry/whole sheets. Compound ingestion must retain one whole logical unit. |
| REF-05 two A4 on A3 scan | AR-20, SC-05 / WP-54/56 | New. Two confirmed non-destructive source regions round-trip to the expected logical pages. |
| REF-06 four small pages | AR-20, SC-05 / WP-54/56 | New. Four independently ordered logical regions reference the same unchanged page. |
| REF-07 open booklet | AR-19/20, SC-05 / WP-56 | New. Left/right proposals or manual definitions preserve configured reading order. |
| REF-08 blank reverse | AR-22, SC-05 / WP-56 | New. Blank can be suggested or marked manually, remains in source and is excluded only through explicit interpretation. |
| REF-09 recompressed duplicate | AR-23 / WP-40d | New secondary acceptance. Different hashes with equivalent rendered content produce a possible-duplicate warning, without deletion. |
| REF-10 alternative edition | AR-22/23, AR-17 / WP-35/40d/56 | Partial coexistence/preference evidence in tests/test_editions.py. Visual matching must retain distinct edition identities and bytes. |
| REF-11 125-piece A5 booklet | AR-25/26, CAT-05 / WP-54/55/56 | New. One source per instrument, 125 searchable work IDs and no mandatory physical splitting. |
| REF-12 five works on one page | AR-20/25, CAT-05 / WP-54/55/56 | New. Five distinct content associations share one source page without identity merging. |
| REF-13 work across pages | AR-20/25 / WP-54/55 | New. Ordered region references cover both page portions and export all selected content. |
| REF-14 different instrument locations | AR-25, CAT-05 / WP-55 | New. Same work ID resolves correct editions with differing page indexes/coordinates. |
| REF-15 Deutsche Messe | CAT-05, EX-11 / WP-55/37 extensions | New. Parent and ordered movements search/select independently and export their confirmed content. |
| REF-16 same-page movements | CAT-05, AR-20/25 / WP-54/55 | New. Independent movement references may share a page and continue across pages. |
| REF-17 selected collection song | EX-11/13 / WP-37/39 extensions | New. Selected confirmed regions only, correct lineage, unchanged original hash. |
| REF-18 entire collection | EX-11/12 / WP-37/39 extensions | New. Original logical sequence and explicit shared-page handling reproduce complete collection content. |
| REF-19 A5 two-up A4 | PT-06/08 / WP-57/38 extensions | New. Two units per simplex sheet or four per duplex sheet, proportional fit and margin containment. |
| REF-20 A5 four-up A3 | PT-06/08 / WP-57/38 extensions | New. Four units per simplex sheet or eight per duplex sheet, correct slots/scales. |
| REF-21 multi-page duplex | PT-09/10 / WP-42/45 | New. Independent slot oracle reconstructs front/back order for long/short-edge flips. |
| REF-22 ring binding | PT-08/09 / WP-42/57 | New. Every final-page content box is disjoint from configured protected binding area. |
| REF-23 odd/even margins | PT-09 / WP-42 | New. Mirrored exclusions follow final-page parity for all supported binding edges. |
| REF-24 odd final count | PT-09 / WP-42 | New. Tail reverse side follows configured blank policy and duplex correspondence. |
| REF-25 duplex A3 cut layout | PT-06/09 / WP-42 | New. Cutting the imposed front/back slot mapping yields exact final order and orientations. |
| REF-26 custom march dimensions | SC-03, PT-07/08 / WP-42/57 | Partial stored marchbook configuration. Numerical maximum-fit/custom geometry and rendered legibility are new acceptance. |
| REF-27 annotations at boundaries | SC-02, PT-08 / WP-40c/41/42 | New. Synthetic edge annotations survive conservative/manual crops; uncertain bounds warn. Private visual quality remains separate. |
| REF-28 invalid template | PT-07/10 / WP-57/38/45 | New template acceptance. Impossible dimensions, scale, overlaps and duplex settings yield actionable blocking findings. |
| REF-29 selective replacement | EX-06/14, PT-09 / WP-37c/39/45/46 | Partial targeted/historical exports in tests/test_export_library.py. New insertion case must pin correct work/participant/edition/parity/binding. |
| REF-30 unequal instrument page counts | GR-07/12, EX-14 / WP-32/37b | Partial common-order personal generation in tests/test_personal_generation.py and test_pdf_composition.py. Extend fixture to region editions and verify same position order/numbers across differing physical counts. |
| REF-31 interrupted large processing | OP-02, SC-06 / WP-05/24–27/56 | Partial attempt/recovery evidence in tests/test_job_recovery_sqlite.py. New page/region processing must resume exact revisions without duplicate publication or lost progress. |
| REF-32 scan-to-export source integrity | GR-01/02, AR-26, EX-13 / WP-14/54–56/37 | Partial byte-identical publication in tests/test_archive_files.py and container smoke. Compound end-to-end must retain original/CLEAN hashes while linking derivatives. |
| REF-33 Windows/Linux equivalence | OP-07/09 / WP-06p/08 and processing WPs | Partial shared PDF/process Windows CI and Linux/container CI. Compare equivalent region/layout/OCR results under declared tolerances, with separate native-storage and packaged acceptance. |
| REF-34 shared source page | EX-12 / WP-55/37/38/39 | New. Selected once/regions/repeat policies yield the exact expected source occurrences without omitted selected music. |
| REF-35 cover/contents parity | PT-09, EX-13/14 / WP-37/42 | New. Inserting cover, multi-page contents and blanks updates each final-page binding side deterministically. |
| REF-36 compact selected songs | EX-11/12, PT-06/08 / WP-37a/38/42 | New. Pack confirmed regions into compact output within constraints, preserve occurrence coverage and avoid arbitrary staff/system splitting. |

## Unnumbered source clauses and integration instructions

The section references below cover the narrative clauses and lists as well as
the numbered aliases above. They route to canonical acceptance and preserve
shall/should/may distinctions.

| Source section | Canonical disposition |
| --- | --- |
| Integration instructions 1–6 | AGENTS.md and PROCESS.md retain autonomy, safe continuation, concise deterministic verification and exact-SHA gates. REQUIREMENTS/ARCHITECTURE/DECISIONS/IMPLEMENTATION_PLAN plus this crosswalk and existing domain/traceability docs hold the consolidation. No automatic expanded implementation or destructive real-data migration. |
| Appendix A §1, §21, §22 | GR-16, OP-07/09 and DEC-12/13 establish product direction, shared local application, consolidation versus implementation approval, and the scan-to-content-to-output vision. Competitive product names are motivation, not capability/API evidence or UI-copy instructions. |
| §2.1 entity table and relationship clauses | GR-16, AR-20, CAT-05/06, EX-11/13 distinguish immutable source, source page, logical page, region, work/component/collection, part/edition, template and generated document with many-to-many links. WP-54/55 and the ARCHITECTURE target preserve simple whole-file workflows. |
| §2.2 all preservation clauses | GR-01–06/15, AR-21/26, OP-08 retain unchanged RAW/CLEAN bytes, separate metadata, traceable derivatives and on-demand output without mandatory source duplication. |
| §2.3 deployment/dependency clauses | OP-07, GR-14, WP-06p and PORTABILITY.md distinguish shared logic, native storage, packaged desktop and physical NAS verification. Essential processing is local. |
| §3.1 input scenario list | AR-19/20/22, WP-56 cover complete multi-part/multi-work sets, mixed geometry, booklets, composite scans, blanks, duplicates and genuine large pages. |
| §3.2 segmentation signals/example | AR-19, SC-06, REF-01–03 preserve all signal candidates and continuation semantics without heading-only assumptions. |
| §3.3 composite versus genuine format | GR-11, AR-20, REF-04–07 preserve genuine A3 and reviewed two/four/facing-page interpretations. |
| §3.4 complete editor action list | SC-05, AR-12/13/21 cover visual context, split/merge/order, assignment correction, continuation/blank/exclusion, region/crop/rotation and restoration. Suggestions and inspected confirmation remain distinct. |
| §3.5/3.6 quality and duplicate lists | AR-22 core safety versus AR-23 secondary assessment, WP-40d/56 and REF-08–10/27 retain every listed condition, distinct editions and no destructive deletion. |
| §3.7 inbox | AR-24/SC-07, WP-59/61f retain stable writes, configured analysis, queue/history and duplicate protection, with manual ingestion independent. |
| §4.1–4.3 collection examples/125-booklet/regions | AR-20/25/26, CAT-05, EX-11 and REF-11–14 preserve all independent works, four-to-six works/page, per-instrument sources, multi-page and multi-region references. |
| §4.4 metadata list/inheritance | CAT-06/08 preserve collection/work-specific titles, numbering, publisher/edition/publication, instrument/format, composer/arranger, section/position/regions and explicit overrides with provenance. |
| §4.5 recognition list/partial indexing | AR-08–11/21/25, SC-06 require multi-title/number, cover evidence, differing part geometry and incremental use only of confirmed portions. |
| §4.6 all collection export scopes | EX-11/12/13 and REF-17/18 preserve entire collection/booklet, selected/consecutive works, pages and regions without original fragmentation. |
| §5.1–5.3 composition/relationships/sharing | CAT-05/06, EX-11/12, REF-15/16/34 distinguish parent movements from collections and explicitly handle once/regions/repeat policies. |
| §6.1–6.4 all geometry/arrangement modes | PT-06/08/09, EX-07/11/12, WP-37/38/42 extensions preserve single/multi-up, source/final/sheet/cut separation, A5 density examples, page-preserving versus content modes, and no re-engraving/arbitrary staff splits. |
| §7.1–7.3 complete template/property table | PT-07/08/09, EX-13, WP-57 cover every category, editable defaults, applicable dimensions/slots/duplex/binding/punch/margins/gaps/scales/crops/imposition/blanks/marks/cover/contents/alignment, validation, should-level transfer and historical pinning. |
| §8.1–8.7 all fit/crop/parity clauses | PT-08/09/10, SC-02/03, EX-14 preserve protected-area fit, aspect ratio, all musical/handwritten detail, final-sequence parity, per-cut-page duplex mapping, configurable blanks and should-level readability/turn/start/break options. |
| §9/9.1 preview/validation/manifest lists | PT-10, EX-08/13 require distinct source/content/page/sheet views, warnings/blockers, safe vector/raster preservation and should-level production manifest fields. |
| §10/10.1 project/replacement clauses | GR-07–12/15, PR-01–09, EX-01–14 preserve common order, contents-only numbering, original printed numbers, saved defaults/overrides, different pagination, historical replay and explicit insertion parity. |
| §11.1–11.3 physical locations/inventory/reports | CAT-07, WP-58 preserve the complete location hierarchy, stock/condition/acquisition/cost/notes and report lists, independent of digital availability. Secondary/should. |
| §11.4 lending | CAT-09, FUT-05/WP-61e. Deferred dates/borrowers/sets/parts/conditions, without blocking core. |
| §12 complete metadata/search/alias lists | CAT-06/08, AR-15/25 and WP-60a retain all fields, normalization/spelling/typo/combined filters, edition/location search and explicit alias suggestions without overriding confirmation. |
| §13 complete productivity list | PR-08/09, EX-06/10/14, WP-60b and existing project WPs preserve duplication/order/ensemble/assignments/completeness, add should-level templates/groups/ZIP/estimates/revision comparison/affected participants and optional print progress. |
| §14 initial/later viewer lists | UI-05/06, WP-60c/61g distinguish source/region/song-87/movement/project viewing from deferred tablet/setlist/offline/annotation/performance features. |
| §15.1–15.5 deferred lists | AR-27–30, CAT-09, EX-15, SC-07, UI-06 and WP-61a–h retain license/purchase, mapped inventory import, QR/inventory, important forScore, lending, acquisition, performance/annotations and optional external metadata with separate prioritization. |
| §16 all exclusions | REQUIREMENTS §12 preserves general association administration, finance/fees, attendance/schedules/events/communications, marketplaces/sales, proprietary readers, notation editing and OMR/transcription exclusions. |
| §17.1–17.4 candidate technologies/resources/modules/tools | OP-02/07/08/09, GR-14 and ARCHITECTURE retain deterministic local bounded incremental processing, caches/on-demand output, one heavy worker, recovery, shared modules and tool-first validation. Technologies and optional local assistance are candidates, not mandatory dependencies. |
| §18/§19/§20 | All REF-01–36, EXT-01–18 and FUT-01–07 route above. IMPLEMENTATION_PLAN maps dependency order without renumbering old WPs, promotes no deferred feature and preserves package-level verification. |
