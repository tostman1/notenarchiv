# Matrix view and provenance (WP-33a)

Authenticated German project matrix displays active shared positions × selected
participants. Rows preserve absolute project slot order including explicit reserves;
columns show saved defaults and musical roles, never live member fallback. Each
cell is supplied by `ResolutionSession.verified_resolution`, the same central WP-32
engine intended for future preflight/generation. The presentation adapter translates
reason/warning labels and attaches descriptive parts only; it chooses no music.

Displayed outcomes: desired/effective exact playable instrument/key/clef part,
personal/default/ensemble provenance, exact confirmed PDF UUID and edition origin,
explicit replacement origin, missing/ambiguous/invalid/corrupt states and warnings.
Only usable confirmed byte-verified cells offer local PDF.js preview/direct download.
Invalid fixed choices are not replaced. Reserve cells have no assignment/editor links.
The read-only view foundation is extended by [MATRIX_EDITS.md](MATRIX_EDITS.md)
for direct cell/default editing; atomic batch/reset remains WP-33c. No preflight
acknowledgment or generation/export snapshot is implied.

Bounded initial window: 25 rows × 10 columns, independent pagination preserving
common numbers and other selections. Pagination IDs and resolver graph share the
same SQLite read snapshot; no per-cell I/O/query selection. Safe actual-byte checks
are request-local and reused once per file. Sticky column/header, horizontal scroll
within a keyboard-focusable region and text status avoid color-only feedback.
Further filters/larger matrix resource measurements remain WP-33d/private NAS gates.

Tests compare every displayed cell with the authoritative resolver, exercise
Mathias/Sebi/Riccardo manual part 2, shared reserve non-editability, no GET mutations,
auth/POST rejection, escaped names, selected-only columns, absolute page numbering,
replacement/corruption/missing-role labels, empty/archived projects and shared-file
verification reuse. Browser validates German labels, persistent matrix state and
mobile containment. All fixtures synthetic; actual private NAS acceptance is separate.
