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
for direct cell/default editing and [MATRIX_BATCH.md](MATRIX_BATCH.md) for atomic
batch/reset. No preflight
acknowledgment or generation/export snapshot is implied.

Bounded initial window: 25 rows × 10 columns, independent pagination preserving
common numbers and other selections. Pagination IDs and resolver graph share the
same SQLite read snapshot; no per-cell I/O/query selection. Safe actual-byte checks
are request-local and reused once per file. Sticky column/header, horizontal scroll
within a keyboard-focusable region and text status avoid color-only feedback.
WP-33d adds participant-name, exact participant, saved-default instrument variant
and deviation filters. Deviations include personal/ensemble/substituted/unresolved
assignments; personal-only and issue-only modes are available. Deviation filtering
applies **within the current 25 × 10 window**, after byte-verified resolution, and
preserves absolute numbers and column alignment. It changes no list or assignment.
Empty windows are honest; inspect other pages too. Participant/instrument filters
apply before column pagination. State survives navigation and edits, including the
no-JavaScript fallback. Page jumps/HTMX navigation replace only the bounded panel;
no fragment retains an obsolete project revision.

Header part choices are loaded once per response and reused across default/batch
dropdowns; POST ModelChoiceFields still validate current active parts. Arrangement
alternatives, signed tokens and byte verification remain request-local/per-file.
No global integrity cache trusts old bytes or approvals. Archive model/reference
verification SQL scales with distinct files, not cells, and is retained for safety.

### Actual synthetic performance evidence (2026-11-23)

Windows/Python 3.12 test client, fully rendered authenticated responses, two tiny
confirmed PDF alternatives for one repeated arrangement; no real data:

| Case | SQL queries | Response time (single sample) | HTML bytes |
| --- | ---: | ---: | ---: |
| Three positions × three people | 105 | 0.759 s | 45,824 |
| 100 positions × 50 people, 25 × 10 window | 105 | 3.306 s | 1,194,732 |

Final targeted rerun after reload-preserving URL navigation: small response
105 SQL/0.360 s/45,850 bytes; large window 105 SQL/2.422 s/1,194,290 bytes.
These are independent single samples, not an average or a guaranteed improvement.

`test_synthetic_100_by_50_bounded_render_queries` enforces equal query counts as
cells grow with the same physical inputs; actual timing/size have no invented SLA.
`test_large_matrix_browser` exercises the last window, sticky header/column, exact
filters, numbering and no-JavaScript reload. These are not measurements of a
heterogeneous 100-piece archive: unique files still need bounded hash/model checks
and more alternatives increase HTML size. Pagination remains necessary; no full
5,000-cell DOM is rendered. NAS CPU/RAM/filesystem/latency acceptance is separate
(WP-52). Existing 200 alternatives/arrangement, 512 MiB alternative verification
and 60 s integrity budgets remain unchanged.
Header part inventory is limited to 2,000 active parts to bound dropdown rendering;
oversized catalogs fail explicitly rather than silently truncating available choices.

Tests compare every displayed cell with the authoritative resolver, exercise
Mathias/Sebi/Riccardo manual part 2, shared reserve non-editability, no GET mutations,
auth/POST rejection, escaped names, selected-only columns, absolute page numbering,
replacement/corruption/missing-role labels, empty/archived projects and shared-file
verification reuse. Browser validates German labels, persistent matrix state and
mobile containment. All fixtures synthetic; actual private NAS acceptance is separate.
