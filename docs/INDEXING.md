# Indexing and STATUS publication (WP-15)

## Scope and entry point

`manage.py index_archive [--folder canonical/RAW-relative/folder]` queues a
durable `INDEX_SCAN`; omit `--folder` for the whole archive. The command emits
only its job UUID. Run the separately validated worker to perform effects.
This backend/operator entry point is not the WP-16 selection UI, and does not
change the published web-only preview installation or deploy a worker.

Selections are recursive. Concurrent overlapping scans are rejected; identical
active or uncertain selections reuse their job. Independent folders may queue.
Jobs/progress/errors remain available in the existing authenticated job UI.
No approval, arrangement assignment, OCR, release or NAS access is performed.

## Durable inventory and copies

- Complete descriptor-relative no-follow inventory is persisted before processing.
  Directory/special-file/link errors cannot justify missing-source inference.
  A failed traversal leaves known source presence/history untouched.
- Walks are bounded to 10,000 entries, 64 path components and 120 seconds between
  syscalls. Source reads stream SHA-256 in 1 MiB chunks and retain at most the
  configured PDF ceiling (100 MiB maximum). Size/mtime never proves equality.
- Each PDF read rechecks descriptor/path stability against its recorded inventory
  fingerprint. Source path/hash/size/mtime and isolated PDF geometry are stored.
  Invalid PDFs retain source hash/validation evidence but never get usable copies.
  Non-PDF regular files are inventoried as skipped; unsafe entries are failures.
- Valid new bytes get an independent, verified `_Ungeprueft` CLEAN copy through
  WP-14, with the same worker fence, durable effect receipt, retained-inode crash
  recovery, no-clobber destinations and protected publication history.
- WP-19 analyzes filename and actual bounded text-layer evidence. Scans remain
  pending actual visual inspection; OCR remains WP-24/25. No automatic proposal,
  inspection, approval or assignment is fabricated.
- Repeated hashes reuse existing available copies after managed-byte verification.
  Changed hashes create separate pending versions. Missing RAW never removes CLEAN
  or previous confirmed versions. Integrity/reanalysis UI remains WP-27.

## STATUS contract

STATUS must be physically/canonically distinct from RAW/CLEAN/PROCESSED/DATA;
unsafe overlap is rejected before indexing metadata/effects. All roots use WP-14
descriptor-relative primitives; unsupported Windows publication fails closed.

Each source folder gets `INDEXSTATUS.json` and one
`_INDIZIERT_BITTE_PRUEFEN.txt` in the mirrored STATUS tree. JSON holds folder/scan
UUIDs, fingerprint, timestamp, indexing counts, missing sources and independent
candidate/review counts, not music text or member data. The German marker prompts
individual visual review; it is not proof of completeness or approval.

Snapshots persist before marker publication. Short fenced effects use exclusive
private staging, file/directory fsync and durable operation intents. Only exact
DB-backed previous snapshots or the fixed application marker may be replaced;
unknown/modified files and symlinks are never overwritten. JSON is authoritative;
the two files cannot be atomically published together, and partial/uncertain
effects remain recoverable/visible as non-successful jobs. Pending recovery requires
the retained stage/final inode, not just equal bytes. STATUS is derived metadata,
not a historical music file store. Dedicated single-writer managed-root permissions
remain required, as for WP-14. No marker helper ever receives a writable RAW root.

## Recovery and remaining gates

Atomic metadata checkpoints resume per-file work after worker death. Completed
copy receipts are reused, rolled-back inventories are rebuilt, and ambiguous
effects block automatic retry. Cancellation uses the existing cooperative worker
contract; filesystem effects are never rolled back by deleting historical files.
Per-file failures produce `PARTIAL_FAILURE` folders while the scan can finish its
safe independent work. Traversal/STATUS failures fail the job; detailed fixed
codes remain in scan/entry records, without private filenames in technical logs.

Synthetic Linux acceptance exercises actual worker copy/STATUS effects and deaths
during inventory, copy publication and marker publication, repeated/changed hashes,
missing/corrupt sources, external conflicts and RAW before/after identity. Private
NAS ACL/mount/fsync/power-loss/performance acceptance and the backup gate before
real ingestion remain unperformed. Kernel filesystem calls can still stall beyond
cooperative deadlines; no false hard-timeout or exactly-once guarantee is made.
