# Direct archive downloads (WP-23b)

Only confirmed compatible ArchiveFile/ArchiveAssignment identities are accepted,
with validated publication receipt and actual SHA-256/byte size. No project/member
or generated output exists in this flow. Versions are chosen explicitly by file UUID;
preferences are not consulted during download and no version is substituted.

Individual GET returns an existing unchanged PDF as an attachment. Multi-selection
POST first shows exactly one copy per selected physical PDF; duplicate file UUIDs
are rejected, including accidental selection of the same combined-part PDF twice.
Confirmed combined parts remain one PDF, never split. Actor-bound signed selection
tokens pin IDs/revisions/hashes/paths for 15 minutes; POST/CSRF download revalidates.
Multiple files produce ZIP_STORED, not merged/generated PDFs. Native A3/A4/custom
sizes, vector/content/metadata bytes remain exactly unchanged; no numbers or stamps.

Limits: 20 PDFs, 100 MiB each (also respecting deployment PDF_MAX_BYTES), 512 MiB
total, 1 MiB chunks, 15-second per-file reads, 60-second preparation/check budget.
One cross-process download slot stays held through response close; stream reads
stop after two minutes. Socket/backpressure cleanup is also bounded by the existing
web server timeout. Private anonymous temporary file under DATA download-scratch,
no archive/EXPORT writes, no persistent output artifacts. Source handles use existing
POSIX no-follow or Windows handle-verified read policy. Reject unsafe scratch paths.
Copy/hash and independent staged PDF/ZIP-member hash verification finish before
HTTP headers; recheck exact current DB selection then stream only private immutable
bytes. Failure/disconnect/response close releases stream and lock; no automatic retry.
Backup excludes this regenerable scratch/lock. Crash orphan cleanup on Windows
remains operator-controlled; no broad automatic delete is introduced.

Authenticated/no-store/nosniff/sandbox attachment responses; no private paths/parser
errors in user messages. Confirmed PROCESSED derivatives use the existing local
PDF.js preview, but only after their own explicit approval/hash verification.
Pending RAW/CLEAN review preview behavior remains unchanged; downloads are stricter.

Tests cover auth/CSRF, exact bytes/ZIP order, A3/A4/combined part, duplicate rejection,
limits, actor/stale token, tampering, state changes during staging, immutable response,
close/lock cleanup, symlink rejection, confirmed derivative preview and no project.
Browser tests inspect actual downloads; hardened container acceptance stages PDF/ZIP
with non-root identity, read-only RAW and network disabled. Private NAS acceptance
and printing/generated-artifact lifecycle are separate later gates.
