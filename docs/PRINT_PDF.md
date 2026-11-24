# Regular print PDFs (WP-38b)

`Processor.compose(..., with_manifest=True)` returns reading bytes plus explicit
logical page origins. Covers, contents, placeholders, reserves and each position
retain separate identities. `Processor.print_pdf` independently validates the exact
page inventory, invokes WP-38a's planner and renders it in the existing resource-
limited PDF subprocess. Reading output is never replaced.

Paired A4 pages use separate Form XObjects with their original vector resources,
content and transparency groups, normalized rotation/UserUnit matrices and left/right
placement on exact A3 landscape. Form bounds and transformed corners are checked;
no fitting, overlay or additional crop is introduced. Whole pages reuse safe-copy
geometry. Native A3, landscape/custom/cropped pages are not split or paired. Existing
annotation/action safety and limits remain; visual annotations fail closed.

Completed reading runs expose an actor-bound, CSRF-protected **separate print PDF**
action. A new immutable snapshot/run copies exact source pins/options/acknowledgements,
sets output_variant PRINT, and records protected source provenance. Worker never
re-resolves mutable project assignments. FULL, EXCERPT, CONTENTS and ARCHIVE_NOTES
are supported. MARCHBOOK and A4-only fallback are explicitly not enabled.

Artifacts have an explicit READING/PRINT variant. Print runs are independently
published through existing verified private stages, fenced no-clobber receipts and
complete-batch manifests. Manifest includes page origins, deterministic physical
sheet plan, transforms, source geometry, side/order, warnings and actual page count.
Partial/failed/uncertain print results are not downloadable. Reading history remains.

The German UI shows variant, page count and media dimensions and offers local PDF.js
canvas preview and download. Preview reuses same-origin assets, disabled scripting/
forms/actions, strict security headers and complete-run/hash gating. No printer is
required or contacted. Hardware printable margins/media acceptance remains separate;
custom sheets preserve original size with an explicit warning, no silent shrinking.

WP-38b introduces the minimum project-free archive snapshot/pin infrastructure
needed for archive print artifacts: exact confirmed selected files/order, no fake
project/participant, protected relational versions/hashes, bounded byte/PDF inspection,
actor-bound request replay and short metadata recheck. Existing unchanged archive
downloads remain available. WP-39 still owns unified library, broader archive-reading
UI integration, targeted regeneration/stale classification; these are not claimed here.

SQLite remakes temporarily remove and reinstall guards inside migrations before
application use. Nullable archive pins have ordinal uniqueness; history stays immutable.
The minimal archive schema is introduced here because WP-38b itself requires archive
print PDFs; no fake project shortcut is used. This implements a prerequisite slice
of WP-39's archive artifact integration without claiming its library/stale scope done.
Tests cover source preservation, arbitrary page runs, media/rotations/UserUnit/crop,
both halves' visual equality at exact physical pixel scale, generated boundaries,
invalid inputs, auth/CSRF/replay and real Linux no-clobber/crash/cancel recovery for
all four kinds. Browser/container tests cover actual print preview/download. NAS,
load/power-loss/musical quality and physical printer gates remain unperformed.
