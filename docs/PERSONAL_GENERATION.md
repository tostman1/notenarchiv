# Personal reading folders (WP-37b)

Authenticated preflight authorizes full folders only with all active shared positions
(including reserves) and explicit acknowledgement for every missing requested cell.
The worker uses WP-36b's immutable payload and relational part/version/hash pins;
it never resolves current project state. Inventory, eligibility and actual bytes
are checked independently. Later defaults, overrides, names or list edits cannot
mutate queued or historical output.

One reading PDF per selected participant contains optional personal cover, German
shared contents without page numbers, exact confirmed music and acknowledged missing
placeholders. Reserves appear only in contents. WP-37a preserves original geometry,
rotation, CropBox/UserUnit and vector streams. No marks are added to music and no
pairing/imposition occurs. Cover labels use snapshot catalog metadata.

## Durable publication

`ExportPublication` reserves a unique human-readable project/person/run path before
composition. Names are bounded, SMB-safe and UUID-disambiguated. `ExportStage`
records verified size/hash, pages, snapshot, person and logical/input inventory.
Private EXPORT `.staging/<publication>/attempt-N.pdf` files use exclusive creation,
independent byte readback, PDF inspection, 0440 permissions and fsync.

The worker intent uses a stable publication UUID. Its fenced callback is only the
short same-filesystem no-clobber link; APPLIED receipt and artifact metadata commit
together. Pending recovery requires matching stage/final inode AND expected bytes,
not merely an equal hash. Unrelated files are never overwritten or adopted. Uncertain
effects require review. Absent effects permit bounded retry with new attempt stages.

After all participants and bytes are verified, `ExportCompletion` pins the exact
batch inventory. Only SUCCEEDED jobs with matching completion, receipts and current
artifact hashes expose authenticated downloads. Failure/cancellation after one person
preserves that effect but exposes no partial batch. ORM immutability, PROTECT and
SQLite UPDATE triggers protect history. No destructive retention is implemented.

Recovery requires the canonical worker process lock, not lease expiry alone. Applied
stage links detach after metadata; uncertain linked evidence remains. Dead-attempt
unlinked stages and owned parser scratch are individually pruned. Linux parser
children are tied to parent death; Windows retains Job Object containment. Failed
cleanup requires review instead of another heavy attempt.

## Bounds and acceptance

Serial composition: 100 MiB aggregate music input/output per person, 512 MiB run
output, 30-minute cooperative deadline, existing 500-page and isolated 384 MiB/
30 CPU-second/60-second parser limits. Staging has a 120-second deadline. Kernel
filesystem stalls are not claimed preemptible. Downloads validate the batch serially
without accumulating all PDFs, then serve one independently verified byte snapshot.

Personal composition, download, snapshot/persistence and real Linux publication tests
cover exact parts, immutable inputs, auth, corruption, process death/reopen/replay,
partial batches, missing/corrupt staging and cancellation. The real personal browser
test covers preflight, worker and download on Linux. The network-disabled hardened
container smoke generates two verified personal PDFs. Results belong in PROGRESS/PR.

Windows publication fails closed; no Windows test establishes NAS fsync/ACL/power-loss,
load or musical visual acceptance. No NAS, deployment, release, printing or OCR.
