# Secure PDF preview — WP-18

## Contract and integration

Requirements: AR-12, OP-03, GR-14. This package provides a reusable preview,
not a library, recognition service, inspection action or approval workflow.
WP-19 is not required. No archive schema or recognition module is changed.

Use `reverse("archive_preview:viewer", kwargs={"file_id": archive_file.pk})`
from future review/library screens. The namespace is mounted at
`/archive/preview/`. Every business endpoint requires a logged-in active
archivist with the existing common rights. UUID secrecy is not authorization.
Source/version/job IDs, arbitrary paths and unpublished files are not accepted.

Only available, structurally validated, BASE/CLEAN records with exact applied
publication receipts are eligible. Pending, approval-requested and confirmed
versions are previewable; rejected/withdrawn, missing/corrupt, PROCESSED and
staging inputs are not. Preview never creates an inspection or changes review
state. Future WP-20 must explicitly record the archivist's inspection.

The document endpoint verifies size and SHA-256 on every request and returns
the original immutable bytes. POSIX reads use the existing no-follow,
descriptor-anchored root reader. Windows development rejects reparse points
and validates the opened file handle's final path. Read limits apply before
allocating large buffers. A maximum of two hard links accommodates the retained
publication staging inode; root/path/hash/receipt identity remains mandatory.

## Browser boundary

PDF.js 6.5.438 is locally bundled with its worker, CMaps and standard fonts.
No runtime CDN, telemetry, service worker or external asset dependency exists.
The custom canvas-only viewer has page selection, previous/next and zoom.
It does not install PDF scripting, XFA, annotations/forms, links/actions,
attachments, metadata HTML, print or download controls. Evaluation and WASM
are disabled. Images and canvas dimensions are bounded. An unsupported page
fails visibly; no automatic sanitization rewrites CLEAN music.

Document responses use `application/pdf`, attachment disposition with a UUID
filename, a sandbox CSP and `nosniff`; they are fetched as bytes by PDF.js,
not embedded through a browser PDF plugin. The viewer's CSP restricts scripts,
workers, fonts and connections to local assets; objects and framing are denied.
All responses disable caching and use same-origin resource/referrer policies.
Authentication failure, missing/corrupt data and parser/native failures never
expose paths, document text or exception details.

## Thumbnail resource policy

`thumbnail/<page>/` accepts only a one-based validated page number. Edge length
is fixed at 256 pixels, with 262,144 render pixels maximum, 1 MiB output,
15-second subprocess timeout and 10-second CPU budget. Existing WP-17 parser
memory/structure limits and child process isolation remain active.

A nonblocking OS lock under private DATA permits only one native preview
render across web processes. Busy requests fail safely and may be retried
manually. Private temporary staging is removed on completion/failure. There is
no persistent thumbnail cache and therefore no unbounded per-file cache growth.
The web service writes only DATA; RAW/CLEAN/PROCESSED are never modified.

## Acceptance evidence

- `tests/test_preview.py`: pending/confirmed exact bytes, no review mutation,
  login, unknown/unrelated IDs, traversal and tampered paths, receipt/state
  gating, missing/corrupt/oversize inputs, native error sanitization, actual
  bounded thumbnail and cleanup. POSIX symlink negatives execute in Linux CI.
- `browser/test_preview.py` + `browser/preview.cjs`: real PDF.js worker and
  nonblank canvas for vector/scan A4/A3 fixtures with active actions, navigation,
  zoom, reload, local-only requests, thumbnails and logout/access denial.
- Local Windows checkpoint: 20 preview tests passed / one POSIX skip; all five
  browser tests passed. Full suite and PR/Linux/container CI are recorded in
  the PR delivery evidence, not presumed here.

NAS resource, filesystem and private real-music visual acceptance remain
separate. No release, merge, deployment or actual association-data use is
performed by WP-18 implementation authorization.
