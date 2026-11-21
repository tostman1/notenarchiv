# Archive metadata and state contract (WP-13)

This package supplies metadata and short transactional services, not ingestion,
filesystem publication or a review UI. WP-14 owns verified physical publication;
WP-18/20a own authenticated preview and explicit visual review. None of this
source functionality is in the immutable published preview image.

## Identity and history

`SourceFolder` records inventory status/counts and non-exclusive arrangement
proposals. A folder association never assigns all its files. `SourceFile` is
identified by the exact RAW-relative path and retains its current observation.
`SourceVersion` is unique by `(source_file, sha256)`: equal hashes in different
source files remain separate musical identities. Reobserving a previously seen
hash reuses its version and validation without changing its original timestamp.
Changed hashes create versions; missing RAW retains all versions and CLEAN copies.

An `ArchiveFile` has a direct nullable arrangement, immutable content identity,
root-relative destination and independent candidate, review and availability
states. A base copy belongs to CLEAN and must match its source version's hash and
size. One base identity per source version prevents duplicate inventory imports.
Derivatives belong to PROCESSED with separate hashes, protected provenance and
immutable processing profile/version. No derivative inherits approval.

All persistent references use PROTECT. Services retain history rather than
delete/reuse identities. Paths are canonical relative references; managed
destinations additionally reserve NFKC/casefold-equivalent keys. This lexical
validation does **not** authorize filesystem access or defend against symlink
races; the filesystem layer must open paths safely against configured roots.

## Review and publication transitions

1. A structurally validated source can register an UNPUBLISHED base identity.
2. A FileOperation reserves an exact destination/content identity. STAGED binds
   a job attempt and private `.staging/` reference. APPLIED requires the exact
   protected attempt and APPLIED durable OperationIntent, including effect key,
   payload and root/path/hash/size receipt. Only then is availability acknowledged.
3. A proposal seals a revision, arrangement and distinct controlled part set.
   A new proposal never changes an existing approved assignment. Recognition
   candidates (including confidence 1) and folder associations cannot approve.
4. An explicit ReviewInspection binds the active reviewer, sealed proposal and
   exact hash of an available validated copy. Merely opening a preview is not
   an attestation. A new proposal requires a new inspection; other reviewers'
   inspections cannot authorize this reviewer's approval.
5. DRAFT -> APPROVAL_REQUESTED requires an active arrangement, nonempty active
   parts/variants and that reviewer's inspection. Pending requests block edits.
   A canonical publication must complete for this exact proposal before
   APPROVED/CONFIRMED and the approved part assignments can be committed.
6. Rejection retains the proposal/inspection. A rejected correction leaves an
   older approval usable. Explicit withdrawal excludes the file from new use,
   preserving approved snapshots, assignments, bytes and audit records.

Publication failure cannot confirm a file. The framework does not claim that a
SQLite transaction atomically covers external writes. WP-14 must persist intent,
perform safe no-clobber effects and reconcile uncertain outcomes. The metadata
stage/receipt/approval functions must run inside the current worker's short fence;
they do not hash bytes, perform I/O or accept an HTTP success boolean as evidence.

## Independent states and transactions

Index progress, source presence, recognition candidates, review and CLEAN
availability are independent. RAW disappearance, partial indexing, a new source
hash or a new candidate/proposal does not revoke an older confirmed copy. Missing
or corrupt CLEAN excludes new use while retaining its historical review decision.
`ArchiveFile.objects.usable()` and `ArchiveAssignment.objects.usable()` centralize
selection; callers must also verify current physical bytes before use. Inactive
catalog identities are excluded. Assignment selection matches the current approved
proposal, including combined PDFs with multiple explicitly approved parts.

Services take SQLite's write lock with the first transactional statement, then
reload and validate protected references. Reviewer edits compare an expected
revision and increment it atomically. Failed validation rolls back all metadata,
including revision/audit updates. No SELECT FOR UPDATE or long file-processing
transaction is used. Filesystem callers must not implement their own weaker
fencing or approval path.

Audit data is local, bounded and relationally pinned. Recognition excerpts and
regions are bounded local DB evidence, never logs or external service inputs.
Model validation and DB checks enforce complementary constraints. Direct SQL,
bulk updates/deletes and bypassing services are not supported application APIs.

## Verification boundary

Synthetic DB tests cover equal content, multiple assignments, reference retention,
invalid metadata/states, exact inspection and publication evidence, rollback,
orthogonal states and withdrawal. A real file SQLite test migrates twice, races
independent connections against one revision and reopens in a new interpreter to
verify history, inspections, assignments, receipts and database integrity.
Metadata fixtures deliberately construct synthetic ledger evidence; they do not
claim an actual copy or NAS operation. Those physical gates belong to WP-14 and
separately authorized NAS acceptance.
