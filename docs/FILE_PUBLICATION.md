# Safe file publication (WP-14)

This is the physical publication backend, not indexing or a review UI. Those
remain WP-15/16/18/19/20a. No real archive is authorized for development. The
published preview image, configuration.yaml digest and release assets are unchanged.
Full worker Compose/operations and private NAS acceptance remain separate gates.

## APIs and ownership

`apps.archive.publication.queue_copy(source_version_id)` reserves an independent
CLEAN base identity and durable ARCHIVE_PUBLISH job. Structurally valid source
metadata is required; the worker independently validates actual staged bytes.
An already available version or active copy job is reused, without automatic
reanalysis/review. A new source hash remains a separate pending version.

`queue_canonical(proposal_id, actor, expected_revision)` records the explicit
inspected approval request and job atomically. Canonicalization reads the verified
managed copy, so missing RAW does not prevent review. It creates another verified
physical copy and updates the file identity's selected path only after success;
old paths remain protected through FileOperation history. It never modifies or
deletes the original CLEAN bytes or RAW. PROCESSED canonicalization stays in
PROCESSED; this package does not generate/enhance derivatives.

`verified_bytes(file_id)` returns bounded, exact-hash managed bytes, including
pending review copies. Callers must authenticate and enforce their selection
policy; a download must additionally require a usable confirmed assignment.
No client-supplied path, arbitrary root or automatic approval is accepted.

Only the real registered worker handler performs physical effects. NAS
`manage.py run_worker` requires non-root identity, current migrations and WP-09's
service-aware storage validation: RAW read-only, managed roots writable, local
SQLite, protected read-only secret and read-only container root. Starting a
container worker service is not added to the published preview installation.
Stop **both web and any manually started worker** before migrations/maintenance.

## Copy and recovery protocol

1. Open configured roots and every path component with descriptor-relative,
   no-follow POSIX APIs. Refuse overlapping roots, symlinks, special files,
   hardlinked sources, traversal and unsupported platforms. Source descriptors
   are always read-only. RAW is never probed by writing, renamed or chmodded.
2. Stream into `.staging/<operation-uuid>/attempt-<number>.pdf` on the destination
   filesystem with exclusive creation and private directories. Limit input to
   the configured ceiling (at most 100 MiB), use 1 MiB chunks, SHA-256 and
   before/after descriptor plus pathname fingerprints. Read the stage back
   independently, compare its hash/size and inspect the PDF in the isolated core.
   Staged data is immutable 0440 after writing and fsynced with its directory.
3. Record the verified stage under the current job/attempt/OS-owner fence. Persist
   the generic durable intent before effects. In the short final fenced callback,
   recheck canonical approval eligibility, use exclusive same-filesystem
   [os.link](https://docs.python.org/3.12/library/os.html#os.link) to publish the
   stage without replacing any destination, check inode/type/case spelling and
   fsync the target directory. This is a new copy inode, never a hardlink to RAW.
   Known refusals before the final effect become ABANDONED; uncertain I/O remains
   pending. Parent preparation occurs outside the final DB transaction.
4. In the same short SQLite transaction as the APPLIED receipt, the handler's
   **pure metadata** acknowledgement records FileOperation and availability;
   canonical approval also commits inspected assignments. Only then detach the
   private stage link. There is no atomic DB/filesystem or exactly-once claim.
5. After a dead predecessor releases the canonical OS worker lock, reconciliation
   requires expected bytes **and the same retained stage/final inode** before
   acknowledging a pending effect. An unrelated replacement is never adopted,
   even with equal bytes. Missing destination permits bounded retry; ambiguous
   effects require review. Recovery repeats file/directory fsync before acknowledging.
   Prior dead attempts' private unlinked stage files can
   be removed individually under their protected attempt records; no recursive
   deletion or cleanup of final/history files occurs.

Cancellation before publication leaves no available copy. Cancellation after an
effect cannot undo it: recovery still records the actual file/receipt, even if
the job is cancelled. If approval eligibility was withdrawn during a crash,
recovery retains the new physical effect as history, keeps the previous selected
path/withdrawal and rejects the request instead of restoring approval. A subsequent
attempt reports REVIEW_REQUIRED. A retained APPLIED stage link can be verified
read-only for pending preview, without exposing staging as a URL.

## Names, limits and verification

Names preserve display metadata independently, normalize Unicode, disarm SMB
reserved names/characters, bound UTF-8 component length and include title,
arranger/edition, instrument, notation/key and combined part codes. Equal-title
works get distinct work suffixes. Case/Unicode-equivalent destination keys are
reserved in the DB; actual directory spelling is reused. Existing destinations,
including identical bytes, get a stable version suffix when necessary. A new
external race/conflict is retained and reported, never overwritten. Managed
directories must have a single authorized application writer in production.

Path walks have at most 64 components; directory collision scans stop at 100,000
entries. File reads/copies have a 120-second checkpoint deadline, PDF validation
has its own 60-second/30-CPU-second and 256-MiB child limit. Checkpoints bound work
between syscalls; Python cannot impose a hard deadline on a stalled kernel
filesystem call. Publisher ownership is retained rather than pretending it stopped.
Actual NAS filesystem/fsync, resource/load and power-loss behavior remain private
hardware gates. Windows physical publication fails closed; there is no weaker
resolve-then-open fallback. Linux CI and the actual hardened amd64 image must
exercise physical copy/recovery, separately from Windows metadata/naming tests.

Synthetic tests cover independent real copies (including already-correct names),
same/different/case collisions, mutation, symlink/traversal/special files, malformed
PDFs, limits, partial writes/readback corruption, current-owner fencing,
cancellation, independent worker deaths during copy/after link/inside acknowledgement/
after commit, exact recovery and withdrawal. Container acceptance also checks
independent host/mount RAW denials, non-root ownership and a network-disabled
copy -> explicit review -> canonical publication sequence.
