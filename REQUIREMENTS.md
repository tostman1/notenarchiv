# Notenarchiv & Marschbuch-Generator — Requirements

**Specification revision:** 3.0 — 2026-11-25
**Status:** Product specification; functionality is not claimed to be implemented.  
**Audience:** Developers, coding agents and project owner.

## 1. Purpose and scope

Build an independent, locally hosted web application for the music archivists of a music association. The target deployment is a Synology DS224+ running Docker Compose. Digitize sheet music once, archive it reliably and reuse it for any number of projects, including marchbooks, concert folders, entertainment folders and small ensembles.

The application has four main workflows: (1) archive and review scanned music, (2) maintain musical and member master data, (3) create reusable projects and assign music to participants, and (4) generate, download and print sheet music. Scan enhancement is a separate, optional processing workflow.

All technical documentation, code, identifiers, comments, tests, logs and commit messages are English. The user interface and archivist-facing user manuals are German. Use translatable UI strings.

Requirement IDs below are stable. `ARCHITECTURE.md` defines technical implementation; `IMPLEMENTATION_PLAN.md` defines delivery order. Requirements take precedence over architectural convenience. Proposed defaults and unresolved hardware details are listed in `DECISIONS.md` and must not be mistaken for verified facts.

## 2. Non-negotiable business rules

Revision 3 integrates the owner specification dated 2026-11-25, including its
Appendix A. New core requirements are approved product direction. Implementation
of material new content-model and layout scope requires the consolidated decision
in DECISIONS.md. Existing delivery authority continues for unaffected work.
Core uses shall, secondary productivity uses should, and deferred features
remain later work. Source aliases and coverage are recorded in
[the crosswalk](docs/REQUIREMENTS_CROSSWALK.md), which adds no independent requirements.

**Distribution scope (owner decision, 2026-11-25).** Preserve the existing server
edition. A future Windows installer supplies an executable and shortcut, shared
UI, bundled runtime, SQLite, PDF and OCR dependencies. Users choose archive, data
and export directories in application settings. The application owns startup
and shutdown on one workstation. No end-user Docker, Python, database server,
OCR installation or service management is required.

| ID | Rule |
| --- | --- |
| GR-01 | RAW is read-only both at the NAS permission boundary and in the container. No application operation may create, rename, move, modify or delete anything in RAW, including status markers. |
| GR-02 | CLEAN is a separate, independently usable file collection containing real, SHA-256-verified, byte-identical copies. Even a correctly named source PDF is copied. Enhanced PDFs are separate derivatives, never replacements for original copies. |
| GR-03 | Every new or content-changed PDF requires content inspection, even if its filename appears definitive. Filename, PDF text and OCR are evidence, not authority. |
| GR-04 | Every new or changed musical assignment requires explicit human confirmation after visual inspection. Batch confirmation is permitted only for individually inspected versions. No automatic approval. |
| GR-05 | Indexing, review and completeness are distinct states. A fully reviewed piece may still be incomplete. |
| GR-06 | An unchanged, already confirmed source version is not routinely OCR-processed or reviewed again. A changed version needs new review; old referenced versions survive. |
| GR-07 | Each project contains exactly one common ordered list of positions and numbers. All full folders have the same list; there are no personal additions, omissions or numbering schemes. |
| GR-08 | Full folders are personal, one per selected project participant. Independent archive-note exports and project excerpts are separate output types, not alternate full folders. |
| GR-09 | Missing playable music never disappears silently. Warn, require explicit acknowledgement, and include a placeholder for each missing requested position in project output. Never substitute an unconfirmed PDF. |
| GR-10 | Personal position override > saved project assignment; project assignment initially copies the member default. Explicit available selections win; substitution is only for unavailable desired playable parts, never a way to override a deliberate available selection. |
| GR-11 | Never split a native A3 sheet. In the existing regular print mode, only consecutive compatible A4 portrait pages of the same piece can be paired. Preserve reading order. Explicit template-driven layouts use PT-06–10 and confirmed logical regions, while preserving genuine A3 content as a complete logical unit. Composite scanner pages are a separate reviewed interpretation. |
| GR-12 | Piece numbers appear only in the contents, UI and export metadata (or filenames). Never stamp numbers onto note pages, including marchbooks. |
| GR-13 | `DEBUG_MODE` never enables Django `DEBUG`. Authentication and security remain enabled in both modes. |
| GR-14 | Local processing only; no telemetry, external OCR or runtime cloud dependency. No real association music, members, secrets or sensitive OCR content in Git, external AI services, CI artifacts or technical logs. |
| GR-15 | Generated files are tied to an immutable, validated snapshot; later edits never change an already generated file in place. Referenced archive versions are protected. |
| GR-16 | Immutable source files, source pages, logical pages/regions, musical identity/edition and output layout are independent linked concepts. No one-file/one-work/one-part/one-logical-page assumption. Preserve the simple whole-document case. |

## 3. Users and navigation

- **UI-01:** Only archivists use the application. Individual authenticated accounts with identical functional rights are sufficient; no musician self-service, differentiated business roles or public sharing links.
- **UI-02:** German navigation: Übersicht, Notenbibliothek, Indizierung, Prüfwarteschlange, Projekte, Scanaufbereitung, Mitglieder, Instrumente und Stimmen, Aufträge, Einstellungen; Debug / Logs only in Debug mode. Home shows archive review counts, recent projects and job progress using real data.
- **UI-03:** Prioritize practical desktop browser workflows, keyboard-accessible controls, clear labels and error states, few clicks and immediate feedback. Do not rely on color alone for status. Browser reload restores saved state. Show progress, cancellation and actionable errors for long-running jobs.
- **UI-04:** Use controlled instrument/part/notation dropdowns everywhere assignments are made. Free text is permitted for descriptive master data and aliases, not as an alternative to a valid reference.

- **UI-05:** A secondary integrated viewer should navigate complete sources,
  instrumental editions, logical pages, regions, works, movements and project
  documents, with zoom/rotation and direct navigation to song 87 in a collection.
- **UI-06:** Deferred tablet/performance features may include digital setlists,
  offline packages, personal/shared annotations, performance navigation and
  synchronized page turning. A comprehensive performance application is outside
  the initial core release.

## 4. Central archive

### 4.1 Physical archive and indexing

- **AR-01:** Accept existing NAS folders organized primarily by piece, with multiple PDF files per folder. Names may include the title, instrument, part, generic scanner identifiers or combinations. Support scanned monochrome PDFs and digital/vector PDFs, portrait/landscape A4, A3 and marchbook dimensions. Digitization and source placement happen outside the app.
- **AR-02:** Keep RAW and CLEAN physically separate. In simple single-work workflows organize CLEAN by human-readable piece title and arrangement where needed, with standardized PDF filenames including instrument, part number(s), and relevant transposition/notation. Compound-source naming follows AR-26. Use a stable collision suffix only if human-readable names cannot distinguish files. File-system-safe names; preserve display metadata independently. Real PDFs, not links. CLEAN is browsable through File Station/SMB without the app.
- **AR-03:** Record source-relative path, source version, SHA-256, page metadata, destination, arrangement and assignment history. Copies must be verified before publication. Do not overwrite existing unrelated files; do not publish partial copies. Flag duplicate content, but do not automatically merge distinct musical identities.
- **AR-04:** Index the whole archive or a selected folder on demand. Show progress and errors. Mirror source-folder status in a separate STATUS tree and in the UI, e.g. `_INDIZIERT_BITTE_PRUEFEN.txt` plus machine-readable metadata. This is the visible mark for the source folder; nothing is written into RAW. Indexing prompts the archivist to check the parts.
- **AR-05:** Recognize added, changed and missing sources. New content creates a new pending version and requires review. A deleted/missing RAW file never triggers automatic deletion of CLEAN or historical versions. Detect unchanged confirmed versions by hash. Offer a full, manually triggered integrity check that recomputes hashes and verifies file/DB relationships; routine scans may use size/mtime as a performance hint, never as definitive proof of equality.
- **AR-06:** Import unknown or conflicting PDFs into a clearly marked pending area of CLEAN (e.g. `_Ungeprueft`) with a reversible association to their source. Manual correction can rename/move only CLEAN copies and must keep all references valid. Confirmed canonical copies are protected from accidental replacement. Multiple versions may coexist.
- **AR-07:** Support multiple arrangements of a piece (arranger is an important discriminator; edition/label can disambiguate further). Different works can share a title. Multiple source folders may contribute to one arrangement; grouping by source folder is a proposal, not proof.

### 4.2 Content recognition and review

- **AR-08:** Analyze filenames and extract relevant text from PDF content on every new/changed version. For scans or insufficient/unreliable text use local OCR of the heading and, where necessary, additional regions/pages. OCR must not be skipped merely because the filename is clear. The early manual-only workflow must still show the actual PDF for mandatory human inspection.
- **AR-09:** Indexing and OCR are independently startable functions. The index workflow can request OCR for appropriate files; OCR can also be launched explicitly for chosen unreviewed files or after a rule change. Explicit reanalysis of a confirmed unchanged file does not silently revoke its approval or replace its assignment; changed proposals require review.
- **AR-10:** Detect title, instrument, part numbers, transposition and notation, including aliases, Roman numerals, abbreviations and combined labels. Arrangeur recognition is useful when evidence is available, but advanced automatic arranger recognition is not necessary for first delivery. Example: `Trombone II/III` is one PDF assigned to both Posaune 2 and Posaune 3; keep the entire PDF for either part. No splitting of a combined part is required.
- **AR-11:** Compare filename evidence and actual content. Agreement yields a plausible proposal; disagreement is a prominently marked conflict; missing/illegible evidence is uncertain. OCR confidence is not musical correctness. Maintain editable aliases/recognition rules, rule versions and provenance. A fuzzy match alone must not confirm an assignment.
- **AR-12:** Review queue: show source filename, actual PDF with navigation/zoom, relevant recognized region or text excerpt, proposed work/arrangement/parts, method, confidence and conflict reasons. Provide quick previous/next navigation and direct correction using master-data selections. Confirm only after visual inspection. Support multiple assignments to one PDF. Never make unreviewed music automatically available for generation.
- **AR-13:** Support a review workflow that records an explicit per-file-version inspected action for the current reviewer, followed by individual or batch confirmation. Opening a thumbnail, high confidence or selecting all is not proof of inspection. Batch confirmation may only include inspected, valid, unchanged versions. Editing proposed assignments or changing file version invalidates the relevant inspection as necessary. Track reviewer, timestamp and approved assignments in the local audit record.
- **AR-14:** Separate file recognition/review status, source-folder indexing status and arrangement completeness. A changed version or an incomplete scan cannot make the previously confirmed version silently disappear. Show new/changed, unknown, conflict, failed, pending and confirmed states, plus missing source separately.

### 4.3 Search, completeness and editions

- **AR-15:** Live library search matches case-insensitive substrings anywhere in titles (e.g. `ab` finds `ABBA Medley` and `Abel Tasman`, and interior matches such as `Fuchsgraben Polka`). Support aliases and reasonable Unicode normalization; use filtering by instrument, part, arrangement and review/completeness status.
- **AR-16:** Show an arrangement × part completeness view distinguishing confirmed available, unreviewed, missing, not required and unknown expectation. Expected parts are configurable per arrangement, required or optional; allow reusable instrumentation templates to accelerate setup. Do not assume all association instruments are required for all arrangements. Without expectation data, completeness is unknown. The project preflight is an additional independent, participant-specific completeness check.
- **AR-17:** Several confirmed playable versions of one arrangement/part can coexist (e.g. older/newer scans, different editions or approved enhanced derivative). Allow one archive-wide preferred version per arrangement and compatible instrument part. Explicit project/position/participant choices override the preference. A changed preference never silently replaces a pinned choice or old output; identify affected outputs as stale where relevant. If no unambiguous suitable version exists, prompt for selection or use the missing-note workflow rather than guessing.
- **AR-18:** Directly from the library select a work, arrangement, one or more confirmed parts and concrete versions where necessary, preview, download or print the selected PDF(s), without creating a project or member. Shared combined-part PDFs are not split. If the same physical PDF is selected more than once, clearly show how many copies will be exported/printed; avoid accidental duplicates.

### 4.4 Compound ingestion and source references

- **AR-19:** Import complete multi-part, multi-work scan documents in batches,
  including mixed sizes/orientations, booklets, blank backs, duplicate scans and
  composite scanner pages. Propose boundaries using text/OCR, titles, instruments,
  numbering, headings, geometry, whitespace and continuation evidence. Missing
  repeated headings on continuation pages must not alone split a part. The
  1–3/4–5/6–8/blank-9/10–11 example shall yield four reviewable part groups and a
  blank classification. Manual batch ingestion shall work independently of inbox watching.
- **AR-20:** Represent source pages and revisioned logical pages/regions with stable
  identity, original page geometry, units and reproducible transforms. Multiple
  logical pages may reference one scan, including two A4 pages on A3, four cards,
  and facing booklet pages. Composite interpretation requires reviewed evidence.
  Dimensions alone never split genuine A3 music. Multiple regions may span pages
  and documents and shall retain explicit ordering and original source hashes.
- **AR-21:** Segmentation and content associations have explicit confirmation
  boundaries. Record inspected source/page/region revisions and musical assignments.
  Changing source bytes, boundaries, ordering or relevant assignment invalidates
  the affected new-use confirmation and inspection. Retain earlier revisions and
  historical snapshots. Confidence, thumbnails and bulk selection never approve.
  Unconfirmed regions cannot enter new exports. Correctly confirmed portions may
  be used while the rest is visibly incomplete.
- **AR-22:** Core ingestion shall classify blanks manually or by reviewable
  proposals and identify byte-identical sources/pages where deterministically
  possible. Distinguish exact duplicate, possible visual duplicate, repeated page,
  part duplicate and different edition. Never delete, merge identities or omit
  content automatically. Uncertain visual similarity is a warning. Basic safety,
  duplicate and blank handling remain core. Advanced visual detection is AR-23.
- **AR-23:** Secondary scan-quality assessment should flag orientation, skew, noise,
  resolution, contrast, blur, potentially cropped music, dimension and sequence
  anomalies. Advanced perceptual duplicate detection should recognize recompressed
  copies while protecting different editions. Corrections remain non-destructive,
  conservative proposals. REF-09 is mandatory acceptance for this secondary
  capability when delivered, and does not make it a current core-release gate.
- **AR-24:** A secondary configurable watched inbox should wait for stable completed
  writes, register safely, prevent accidental duplicate imports, run configured
  analysis and expose a review queue and import history. It must not write into RAW
  or be required by manual ingestion. Direct scanner/phone control is deferred.
- **AR-25:** Index a 125-piece A5/custom booklet as one immutable source per
  instrument, with four to six independent works per page, including multi-page
  continuations. Search and select each work or movement by identity and original
  song number, even when pages and coordinates differ across instrumental booklets.
  Support multiple titles/numbers on a page, cover-only instrument evidence and
  incremental correction. Page-number equality is never musical identity.
- **AR-26:** A compound source keeps one byte-identical CLEAN base copy with a
  neutral human-readable source/collection identity and collision-safe path.
  Do not imply that a logical excerpt is that unchanged original. Work/part
  associations and original names remain metadata. Cropping, splitting, rotation,
  deskewing, recombination and musical-region export produce traceable derivatives,
  generated on demand where possible, without 125 duplicate source files.
- **AR-27:** Deferred license/purchase records may store receipts, invoices,
  publisher agreements, restrictions and digital/printing permissions. Physical
  ownership never implies unlimited copying/distribution permission.
- **AR-28:** Deferred Excel/CSV inventory import should support column mapping,
  profiles, normalization, preview, validation, duplicates, matching, errors and
  traceable history. It is independent of mandatory PDF ingestion.
- **AR-29:** Deferred QR labels may link stable archive and location identities,
  configurable label printing, record lookup, physical inventory and later lending.
- **AR-30:** Optional external metadata services require separate approval and
  privacy/compatibility assessment. Essential local workflows cannot depend on them.

## 5. Association and musical catalog

- **CAT-01:** Maintain members, instruments, instrument-specific parts, transposition/key, notation/clef and aliases. Instrument display names are not unique identifiers: variants such as B-flat vs C or treble vs bass clef must be distinguishable. Allow equal human names and equal piece titles without merging records. UUIDs provide identity.
- **CAT-02:** Each regular active member has exactly one regular instrument-part assignment. Multiple regular instruments or unassigned regular members are out of scope. Store active/inactive status; referenced records are deactivated rather than destructively deleted. Allow project-specific guest musicians with a valid part without permanently changing the regular membership list.
- **CAT-03:** Maintain explicit replacement rules: e.g. Posaune 3 → Posaune 2, with global, project and position-level scope. Validate musical suitability and avoid implicit cross-instrument substitutions. Rules and aliases are editable without a new image build. No automatic musical transposition or score arrangement.
- **CAT-04:** Distinguish a musical ensemble role from its playable instrument part. Same musical role may be performed by several instruments using different notated PDFs. Instrument families and notation variants are distinct from actual musical roles.

- **CAT-05:** Distinguish collections of independent works from parent compositions
  with movements/sections, including masses, suites, medleys and potpourris.
  Model collection membership, parent/component, arrangement, related edition and
  alternative-title relationships explicitly. A work/part edition may reference
  ordered content across documents/pages/regions, and a region/page may support
  multiple works or editions. Avoid cycles and accidental merging by title.
  Deutsche Messe must support both complete composition and individually searchable,
  selectable and exportable movements, including shared pages and continuations.
- **CAT-06:** Collection metadata includes title, publisher, publication/edition,
  instrument, collection identifier and physical format. Work/component metadata
  includes titles, original song number, composer/arranger, section, collection
  position and region references. Shared values may inherit with explicit local
  overrides. Inheritance must retain provenance and reproducible snapshot values.
- **CAT-07:** Secondary physical archive management should provide configurable,
  searchable building/room/cabinet/shelf/compartment/folder/box hierarchies and
  work/set locations, inventory IDs, copy counts, available/missing/damaged parts,
  condition, acquisition date/cost, notes and availability. Physical and digital
  availability are independent. Printable/exportable inventory reports should cover
  complete inventory, locations, missing/damaged parts, absent digital copies,
  digital incompleteness and acquisition history.
- **CAT-08:** Secondary metadata/search should extend existing titles, aliases and
  instrument/edition filters with publisher/year, genre, difficulty, duration,
  article/external IDs, tags, custom fields, notes, related arrangements,
  collection/movement/location filters and reference recording/audio links.
  Support exact/partial/case-insensitive matching, accent normalization,
  spelling variants, reasonable typo tolerance and combined filters. Local
  recognition aliases improve proposals without overriding confirmed identity.
- **CAT-09:** Deferred lending may track parts/sets, borrower, lending/return dates,
  outstanding items and condition changes. It must not block digitization or printing.

## 6. Projects and shared piece list

- **PR-01:** Create, name, save, reopen, edit, duplicate and archive projects. Persist all configuration across sessions/restarts. One project defines one common musical list, distinct from the catalog Collection entity in CAT-05. Example projects: Marschbuch 2026, Weihnachtsensemble 2026, Unterhaltungsmappe, Konzertmappe.
- **PR-02:** Select pieces from the live-searchable library. Use drag-and-drop to order the positions. A specific arrangement is selected for each piece; an arrangement can occur multiple times and every occurrence has its own stable position ID. Replacing the arrangement in an existing position preserves that position and number; revalidate associated overrides.
- **PR-03:** Automatically renumber after insertion, removal or reordering. The number is derived from the ordered list of positions, including explicit empty reserve slots. A reserve slot consumes a number but produces no sheet page. Example: position 5 reserved, next piece is 6. Moving a piece may shift numbers; preserve explicit reserves as slots and show the resulting contents before saving/printing. See DEC-03 for the precise proposed reserve behavior. Never add numbers to music pages.
- **PR-04:** Select any subset of association members or valid project guests, including select all/deselect all and instrument filtering. Not every project represents the full orchestra. At addition, copy the member's regular part into the participant's saved project assignment. Later master-data changes do not automatically change existing assignments. Offer explicit adoption of updated defaults; preserve deliberate personal overrides unless reset.
- **PR-05:** Persist project name, participant assignments, shared positions and reserves, arrangement references, ensemble mappings, part and edition overrides, replacement rules, cover/layout options and revision. Project duplication creates new identities for project/positions/participants and remaps its overrides. Project edits do not modify association master data or archive assignments.
- **PR-06:** No personal selection, skip, additional pieces or individualized numbering in full folders. A participant may have a different playable part for any piece; if unavailable, that position remains represented by a placeholder.
- **PR-07:** Protect against concurrent lost updates. Show a clear conflict and refresh/retry rather than silently overwriting another archivist's changes. Save and display project revision; outputs remain available after edits, with relevant stale indicators.

- **PR-08:** Secondary productivity should extend project duplication/order/ensemble
  configuration and part/edition assignment with reusable project templates,
  participant/instrument groups, batch documents/ZIP, grouped instrument/section
  exports, completeness/missing-part overviews and estimated printing requirements.
  Keep all full folders on the same project list and numbering.
- **PR-09:** Secondary revision comparison should identify changed works and
  affected participants, select complete regeneration versus replacements and
  optionally track printing progress. Revisions do not mutate historical exports
  and do not turn projects into general event management.

## 7. Assignment and interactive matrix

- **AS-01:** Save a project default assignment per participant. A personal position override takes precedence, including when the normal part exists. Use the saved project default when no override exists; this default originates from the member's regular part, not a live fallback.
- **AS-02:** The matrix is a primary project view: rows are common piece positions, columns are participants. Display effective part, concrete edition when relevant, notation/key, and provenance (saved default, ensemble, personal override, substitution, missing). Reserved rows are not assignable. Fixed piece column/header where useful; filter by instrument, participant and deviations.
- **AS-03:** Change the participant default directly in the column heading or participant list. Edit a cell directly with a dropdown; show relevant confirmed playable alternatives and allow deliberate choice of other valid parts/notation. Do not require separate dialogs for normal changes. Show unresolved desired assignments as such, not as confirmed choices.
- **AS-04:** Select multiple cells of a participant and set a part in one action, with per-position availability checks and clear failure handling. Reset individual or selected overrides to the saved default. Explicit overrides survive default changes. Visually highlight deviations. Persist across reloads. A change must never affect unrelated participants, master data, source data or shared numbering.
- **AS-05:** Separate desired part from concrete edition. Use the most specific explicit compatible edition selection (participant/position, project position, project default for arrangement/part), then the archive preference, then a sole compatible confirmed edition. If alternatives are ambiguous without a preference, report unresolved and let the archivist choose. Expose the source of both part and edition resolution. Exact choices are version-specific; never silently switch an explicit selection. Define clear reset/inherit controls.
- **AS-06:** If the desired playable part is unavailable and no explicit available edition has been selected, evaluate explicit replacement rules from most specific (position) to project to global. Never infer a playable substitute solely from an instrument or part number. Show the actual substituted part and its origin. If no compatible confirmed part is available, report missing. Avoid cyclic substitution; do not silently walk arbitrary fallback chains.
- **AS-07:** Small ensembles: define project musical roles (e.g. 1–4), assign participants to roles, and map (role, instrument/notation variant) to a playable part as a project default. Support a mapping exception per piece position. For example role 3 maps to Posaune 3 for a trombonist and a matching Tenorhorn part for another player. Same role number does not establish compatibility. A personal position choice wins over ensemble mapping. No auto-transposition.
- **AS-08:** Example acceptance scenario: Mathias normally plays Posaune 1, Sebi Posaune 2, Riccardo Posaune 3. Set Riccardo to Posaune 2 for ABBA Medley and several other pieces, even where Posaune 3 exists. Reload, verify persistence, reset one cell and check the others are unchanged. Choose a confirmed bass-clef or treble-clef variant deliberately. All example names are test-only fictional labels.

## 8. Output types and generation

| ID | Output | Scope |
| --- | --- | --- |
| EX-01 | Full personal folder | One PDF per selected project participant, all shared non-reserve positions, optional personal cover, common contents. |
| EX-02 | Project excerpt / reprint | Selected existing positions × selected participants, using the same effective assignments as a full folder. No change to the shared collection. |
| EX-03 | Direct archive-note export | Selected confirmed editions, independent of project or person; single or multiple selections. |
| EX-04 | Contents-only export | Updated common table of contents for a project, independent of complete folders. |

- **EX-05:** Full folders use a common table of contents with piece numbers and titles, no page numbers. Reserved numbers are visible with no note page. With no cover, the contents begin the PDF; an optional personal cover precedes it and contains member name, project and assigned part/role (avoid a misleading claim that all pieces use the same part). Contents may span multiple pages. Excerpts and direct notes default to no extra cover or contents.
- **EX-06:** Export/print one or multiple selected positions for one or multiple participants, e.g. Riccardo lost ABBA Medley and needs the assigned Posaune 2 sheet, or a replaced piece needs reprinting at the same number. Offer this directly from the project/matrix and library as applicable. Reprint may use the current configuration; previously generated outputs/snapshots remain available for exact historical reprints. No full-folder regeneration required.
- **EX-07:** Reading PDF preserves the selected note pages' original dimensions, orientation and visual content (native A3 remains whole). Print PDF is a separate layout artifact; regular A3/A4 or configurable marchbook format. Generated cover, contents and placeholder pages follow project settings. Do not unnecessarily rasterize vector music. No overlay of piece numbers on note pages.
- **EX-08:** Preflight for project outputs displays selected participants/positions/documents, missing parts, substitutions, unreviewed candidates, explicit overrides, ambiguous editions and layout issues. Allow correction before generation. Require explicit acknowledgement of missing parts; place a page with the title and `Noten fehlen` in German at each missing requested position. Invalid/corrupt/unreadable input or invalid selection is an actionable error, not silently treated as valid music. Direct archive exports require confirmed valid selections.
- **EX-09:** Bind the report and acknowledgement to an immutable generation snapshot (project revision, positions, selected people, resolved parts and exact file versions/hashes, edition/layout/cover options, missing decisions). Invalidate the report if relevant data changes before enqueue. All documents in a generation run use the same snapshot. Editing the project during generation does not mutate the run. Archive changes must not silently affect existing exports.
- **EX-10:** Store manifests, generation status and output paths. Only fully generated verified artifacts are downloadable/printable. Mark affected outputs stale after relevant edits or preference changes; retain previous outputs and source versions according to a defined retention policy. Targeted regeneration must be possible. Human-readable output names and folders; protect same-name collisions. Download and optionally ZIP batches. Do not require printing to generate or download a print PDF.

- **EX-11:** Export entire collections or instrumental booklets, selected works,
  consecutive works, pages, movements or confirmed regions without fragmenting
  sources. Support page-preserving and content-based modes. Page-preserving mode
  retains the original song layout. Content mode may compact confirmed short
  works onto new final pages, without arbitrary staff/system cuts or re-engraving.
- **EX-12:** Shared source pages require an explicit deterministic policy. Preserve
  a complete shared page once, extract selected confirmed regions, or repeat the
  page when explicitly configured. Preserve project occurrence identity and order.
  Show consequences before generation. Never silently omit or duplicate music.
- **EX-13:** Extend immutable snapshots/manifests with confirmed content/region
  revisions, source/page hashes, transforms and ordering, effective inherited
  metadata, template revision/configuration, final logical pages, physical sheets,
  duplex mapping, blanks, warnings and production marks. Invalidate preflight
  on relevant changes. Protect relational source/revision references and preserve
  exact historical replay alongside the existing whole-file snapshot schema.
- **EX-14:** Distinguish standalone excerpts from insertion-compatible replacements.
  Replace a work, damaged page, updated edition, movement or selected participant
  pages using the correct position and edition. Insertion replacements should
  reproduce original final-page parity and binding orientation or require an
  explicit alternative. Different instruments can have different page counts
  while preserving identical project work order and numbers.
- **EX-15:** Important deferred forScore interoperability shall preserve stable
  work/part/edition IDs, structured metadata, project order, participant assignments,
  individual content exports and document versions now. Later study official
  capabilities for PDFs, works/parts/full folders/collections, metadata, setlists,
  bulk transfer, updates, duplicate avoidance, identity and supported annotation
  handling. No assumed public API/import format. It must not block the core release.

## 9. Scan enhancement and marchbooks

- **SC-01:** Separately accessible enhancement feature with before/after preview, adjustable parameters, and per-stage enable/disable. Input is a selected archived copy, output a new linked derivative in PROCESSED (or a clearly separated area); never alter RAW or CLEAN bytes.
- **SC-02:** Detect slight skew using staff lines; deskew, conservatively reduce noise and edge shadows, crop excess margins and normalize page format as needed. Preserve staff lines, accidentals, dynamics and every other musical mark. Avoid destructive default filters, warn on uncertain crop/skew, allow bypass. Recheck derivative visual quality before approving it for use. Retain its source, settings, algorithm version and hash.
- **SC-03:** Marchbook is a project format, default 170 × 120 mm landscape, adjustable per project. Normalize print pages to that physical size, preserve aspect ratio and legibility, avoid cropping and allow accurate printing at scale. Reading PDF retains selected input page formats; contents/cover use chosen project format. No printed numbers on music pages.
- **SC-04:** Optional later adapter for already numbered folders by part (e.g. `Altsax-1/01_Radetzkymarsch.pdf`): safely index files into CLEAN and propose a common numbered project list, resolve mismatches, require confirmation. It does not create a separate full-folder mode or bypass review.

- **SC-05:** A graphical segmentation/region editor shall show thumbnails and
  full-resolution sources, boundaries, groups, confidence and associated music.
  Support splitting/merging consecutive groups, ordering logical pages, correcting
  work/part assignments, drawing/editing regions, marking continuations/blanks,
  excluding irrelevant output pages, rotation/orientation, non-destructive crop
  and restoring prior interpretation. Proposals remain distinct from confirmation.
- **SC-06:** OCR/segmentation operates on versioned pages and regions, expands
  beyond headings when needed and supports cover-level instrument evidence,
  multiple small titles/numbers and continuations. Cache keys include exact
  source hash, page/region revision, transforms, processing profile/runtime and
  rule version. Analyze incrementally, preserve provenance and present conflicting
  evidence locally. No filename-confidence shortcut or external AI requirement.
- **SC-07:** Direct scanner and smartphone acquisition are deferred and require
  later prioritization. Initial workflows accept externally produced source files.

## 10. Print layout and printer integration

- **PT-01:** For a run of consecutive A4 portrait pages within one piece, place pairs side by side, left then right, on A3 landscape (420 × 297 mm). Odd remaining page stays A4 portrait. Applies for arbitrary page count, not just the examples. A4 portrait = 210 × 297 mm.

| A4 pages in one piece | Print sheets |
| ---: | --- |
| 1 | A4 |
| 2 | A3 |
| 3 | A3 + A4 |
| 4 | A3 + A3 |
| 5 | A3 + A3 + A4 |
| 6 | A3 + A3 + A3 |

- **PT-02:** In regular print mode, never pair across position/piece boundaries, including repeated appearances of the same arrangement. Do not pair covers, contents or placeholders with note pages. A3 original sheets stay whole; for A4-only fallback a native A3 sheet may be scaled as a whole, never split. A4 landscape, mixed/custom sizes and printable margins need explicit safe layout behavior and preview; never silently crop or distort. Default single-sided physical sheets. Explicit template-driven imposition is governed by PT-06–10 and EX-12.
- **PT-03:** Choose an available/configured network printer in the UI, display capabilities/media, provide print preview, copy count and job status. Use IPP/CUPS where verified. Automatically select A4/A3/custom media only when supported and tested. Preserve page order across mixed formats; if a mixed-media job is unreliable, use consecutive media blocks with an interleaving warning. Do not globally sort sheets by paper size.
- **PT-04:** If A3 or a custom size is unsupported, show a suitable A4 alternative and preview; require explicit confirmation before creating/submitting the fallback. No silent shrinking or clipping. For marchbook custom media, require explicit alternative if actual-size output cannot be achieved. Reading PDFs remain unchanged.
- **PT-05:** Direct archive notes, project excerpts, full folders and contents-only outputs can be printed when supported. Print submission is never automatically repeated after a failure or uncertain acceptance. Show the printer job ID/status when known and request an intentional retry after checking the printer.

- **PT-06:** Extend the same deterministic PDF planner/composer for standard music,
  concert/march folders, songbooks, collections and replacements. Separate source
  geometry, selected content geometry, final musical page size, physical printer
  sheet and cut/fold size. Support one/two/four/configurable n-up, portrait/landscape,
  configured/automatic rotation, simplex/duplex, sequential, cut-and-stack and
  applicable folded booklets. A5 examples shall yield 2/4 logical pages per A4
  sheet and 4/8 per A3 sheet for simplex/duplex respectively. Mixed source formats
  and genuine A3 remain supported. Existing regular exports stay available.
- **PT-07:** Users shall create, duplicate, edit, rename, save and reuse persistent
  print templates, with built-in defaults. Applicable properties include explicit
  millimeter physical/final dimensions, orientation, rows/columns/placement areas,
  page/region mode, simplex/duplex and long/short-edge flip, left/right/top/bottom/no
  binding, clearance/punch geometry, individual outer/printer margins, gaps,
  original/max-fit/fixed scale, per-page/work/output scale consistency, rotation,
  conservative/manual crop, sequential/cut-stack/booklet imposition, blank insertion,
  optional cutting marks/cover, contents and alignment. Validate all parameters.
  Template transfer by export/import should be supported. Pin template revisions
  or exact settings in historical output. Shared edits never alter old outputs.
- **PT-08:** Calculate maximum proportional fit inside printable and final page
  boundaries after outer/printer margins, gaps, binding/ring/punch exclusions,
  cutting tolerance and other configured protected areas. Never distort music or
  use format-specific arbitrary percentages. A continuous binding margin is the
  minimum, conservative rectangles may represent complex exclusions initially.
  Crop whitespace conservatively with review and manual correction, preserving
  titles, instruments, notes, dynamics, articulation, repeats, tempo, references,
  annotations and handwriting. Uncertain bounds cannot silently clip content.
- **PT-09:** Calculate odd/even binding geometry per final logical page after
  covers, contents and blanks, independently of source page numbers or parent
  printer-sheet parity. Support mirrored margins and all binding edges. Deterministically
  map front/back slots, orientation, flip edge, cutting sequence and final order.
  Configurable blanks may complete duplex/booklet sheets, start on a side, avoid
  unrelated reverse-side works or preserve parity, without waste when disabled.
  Where feasible support consistent per-part scale, minimum-scale warnings,
  related-content grouping, reduced turns, front starts and manual breaks.
- **PT-10:** Preview sources, logical music, final pages, physical sheets and both
  sides distinctly. Show printable/binding/punch/content/cutting boundaries.
  Preview aids enter final PDFs only as explicitly enabled production marks.
  Preflight shall block invalid source/region references, unconfirmed content and
  unsafe/impossible geometry and distinguish actionable warnings for missing
  music, clipping risk, exclusions, printable overflow, duplex/pairing and excessive
  reduction. Keep vectors where feasible and avoid repeated lossy compression or
  needless raster resolution loss. Manifests should include project/revision,
  participant/part, works/editions, template/settings, final pages/sheets, mode,
  blanks, warnings and generation time. Validate geometry numerically and visually.

## 11. Operations, safety and quality

- **OP-01:** Local DS224+ deployment, Linux amd64, browser interface, authenticated access over private LAN/approved private remote access. No cloud OCR/telemetry/CDN, no privileged containers. Actual RAM, DSM version and paths must be verified before real-data deployment.
- **OP-02:** One resource-intensive background job at a time, persistent queue, progress, safe cancellation, bounded retries for safe operations and recovery after restarts. Staging and idempotent operations prevent partial/doubled publication. Printing is never retried automatically. Keep memory, PDF sizes, rendering pixels, timeouts and scratch usage bounded; normal browser operations remain responsive.
- **OP-03:** Least-privilege NAS service identity (numeric UID/GID determined on NAS) and read-only RAW at both layers. Secure file operations, no path traversal/symlink escape, no arbitrary request paths, PDF inputs treated as untrusted. Secrets mounted from protected files. No public access. All business routes require login; CSRF and host validation remain active.
- **OP-04:** Deploy is default when `DEBUG_MODE` absent or `FALSE`; `TRUE` enables detailed application diagnostics. Trim and case-normalize; explicitly empty or other values fail clearly. Same image for both services and modes. Django `DEBUG=False` always. Shared Compose setting; recreate services to switch, no build. Debug mode includes authenticated GUI live logs, filtering by job/level/time/component, downloadable sanitized logs and persistent rotating web/worker files. Existing debug logs are not automatically deleted on switching back. Ordinary progress, warnings and OCR review are always available. No runtime GUI switch for this setting.
- **OP-05:** Back up DB and all necessary CLEAN/PROCESSED versions, config/secrets and non-regenerable state consistently; RAW has independent NAS backup. Generated outputs optionally backed up; regenerate only where referenced versions and settings still exist. Restore to isolated environment and verify. Controlled image updates and rollback; no automatic production deployment.
- **OP-06:** Reproducible builds and locked dependencies, local assets, automated tests, synthetic fixtures, verified third-party licenses and notices, versioned container images, clear install/update/restore runbooks. Real-data validation is performed privately on NAS without uploading actual music or members to external services.

- **OP-07:** Server and future single-workstation Windows distribution share UI,
  business logic, data model, ingestion/OCR/PDF/export and essential workflows.
  Isolate safe platform file operations, trusted executables and runtime roots.
  Distinguish shared-runtime tests, native Windows storage tests, packaged desktop
  acceptance and physical NAS acceptance. The final Windows installer is later
  distribution work, with all end-user dependencies bundled and managed startup.
- **OP-08:** Extend data models through safe additive migrations/backfills with
  stable IDs, integrity reports, consistent backup/restore and rollback strategy.
  Preserve confirmed editions, project references and historical outputs. No
  destructive real-data migration is authorized by specification consolidation.
- **OP-09:** Prefer deterministic bounded document/geometry processing and reusable
  validation tools with compact machine-readable evidence when beneficial.
  Reuse existing dependencies after Windows/Linux and license evaluation.
  Incremental page/region processing, cancellation, recovery and caches must keep
  the web UI responsive on DS224+. Concurrency remains capped by OP-02's one-heavy-
  worker baseline until separately approved evidence supports a change.
  PDF libraries, Tesseract, image processing, hashes, aliases and geometry tools
  are implementation candidates, not a mandate to add all dependencies. Optional
  local AI-assisted investigation of ambiguous cases does not relax GR-14 or
  create a cloud dependency.

### Storage authority and recoverability — DEC-15 amendment

This authorized amendment refines GR-01/02, AR-01/02, OP-02/03/05/07/08
without renumbering them or relaxing confirmation, security or privacy rules.

- RAW permits no application creation, modification, deletion, rename, movement
  or overwrite. Independently deny writes: least-privilege Linux/Synology identity
  plus read-only mount; dedicated non-admin Windows identity with read-only NTFS
  permissions, no RAW ownership/mutation rights. Routine execution is non-admin.
  Real account/ACL, production or archive changes are not authorized here.
- SQLite and confirmed/user-generated metadata remain authoritative: preserve
  transactions, appropriate durability settings, version history and consistent
  backup/restore. DB transactions do not atomically commit external PDFs.
- CLEAN stays physically independent, SHA-256-verified, byte-identical and usable
  outside the app, with unchanged naming/version/collision rules. Missing or
  incomplete publication may be reconstructed only from its exact verified source
  version when available. Never overwrite/delete confirmed or historical CLEAN
  because RAW disappeared/changed; CLEAN may be the last surviving historical copy.
- Regenerate outputs/caches only when exact required sources, settings and metadata
  survive. Preserve non-reproducible user work, approved derivatives and necessary
  historical artifacts in retention/backup policy.
- Before potentially mutable PDF/OCR/image/tool processing, copy through validated
  read-only source access into a physically independent working file, verify its
  SHA-256 and detect source identity/metadata changes. Close source handles when
  no longer needed; retain provenance, reuse safe immutable snapshots per job and
  write outputs only to approved roots. No RAW hardlink as a mutable copy, no
  writable RAW tool paths, and no modified working copy published as CLEAN.
  Pure enumeration and streaming hashing require no unnecessary working copy.
- Use validated application-owned scratch and isolated collision-free job
  workspaces, bounded disk/memory/time, safe path/link checks and closed handles
  before cleanup. Detect/clean abandoned workspaces at controlled startup/periodic
  points; protect active jobs and recovery evidence. Never recursively delete an
  arbitrary configured root or escape owned scratch. Disposable cleanup failure
  normally yields a recoverable warning, not failure of an otherwise safe operation.
- External publication requires complete verified staging, appropriate content
  flushing, safe no-clobber destinations/identity checks, persistent operation
  intent, transactional result and reconciliation between DB and actual files.
  Immediate permanence of every new directory, rename or disposable recovery
  deletion across OS crash/power loss is not required. Even acknowledged external
  output may need reconciliation/reconstruction: detect missing, partial, corrupt
  or inconsistent references before treating them as valid. Never blindly retry
  uncertain mutations; preserve files/evidence and require actionable review when
  safe recovery is impossible. Previously confirmed metadata/history remain protected.
- Interrupted import/OCR/generation may need repetition; disposable work/recovery
  files may survive, directories may need recreation, and complete unregistered
  publications may need verification/adoption through operation-bound reconciliation.
  These outcomes are acceptable only when detectable and safely handled, never as
  silent corruption, lost historical content or uncontrolled replacement.
- Shared portability/read-only architecture permits WP-54/55 core development
  independently of remaining Windows write acceptance, production security and
  packaging. Windows writes stay disabled until applicable safety is implemented
  and verified. Do not add another DB, distributed transaction, custom journal or
  storage service merely for recoverability. Process termination is application-
  crash evidence, not physical power-loss proof; investigate hardware behavior
  proportionately to remaining non-recoverable risks and separately approved gates.

## 12. Explicit exclusions and delivery

No musician portal, multi-tenancy, differentiated business roles, individual full-folder piece lists, complete part-only project folders, multiple regular parts per member, automatic transcription/transposition, write access to RAW, automatic print retry or external AI/OCR service. No assumption that all printers support automatic media switching.

General association administration, accounting, fees, attendance, rehearsal
scheduling, general event organization, internal communication platforms,
music marketplaces, publisher sales platforms, proprietary readers, full notation
editing and full optical music recognition/transcription are excluded. Limited
member/performance metadata serves music preparation only. Deferred AR-27–30,
CAT-09, EX-15, SC-07 and UI-06 have separate later approval and do not gate core
delivery. Secondary features retain their should-level priority.

Deliver a useful manual archive workflow first; then OCR, personal project folders and excerpts, scan enhancement and marchbooks, printer integration, and operational validation. The full product includes ensemble support, direct note exports and printing; deferred implementation is not removal from scope. See `IMPLEMENTATION_PLAN.md` for release gates. See `DECISIONS.md` for explicit defaults and actual outstanding validation items.
