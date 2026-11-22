# Implemented acceptance traceability

This incremental register records WP-15 tests, not completion of future packages.
All fixtures are deterministic synthetic data. Physical tests require Linux;
Windows skips are not substitutes for their CI evidence.

| Requirement | WP-15 verification |
| --- | --- |
| GR-01, GR-02, AR-01, AR-02, AR-03 | `test_complete_new_import_verifies_copies_and_raw_is_identical`: independent byte-identical CLEAN copy, source hash/page metadata, no RAW markers and exact RAW inventory before/after |
| AR-04, OP-02 | Selection/payload tests; complete-import STATUS/progress assertions; actual process-death inventory/copy/STATUS recovery |
| AR-05, GR-06 | Changed/missing/corrupt history test; repeated hash idempotence and same-size/mtime change detection; failed traversal never infers missing |
| AR-06, GR-03, GR-04, AR-08 | Unknown pending CLEAN import with WP-19 evidence; no assignment, confirmation or usable files |
| AR-14, GR-05 | Separate folder partial-failure, source presence, validation, candidates, review and publication assertions; STATUS counts are not approval |
| OP-03 | Symlink/unknown STATUS conflict preservation, canonical selection and payload denial; existing WP-14 descriptor/fence and recovery suites remain required |

OCR, human review UI, NAS permissions/load and full integrity UI remain separately
scoped work packages; this register does not claim those gates were exercised.

## WP-16

- AR-04/UI-03: `tests/test_index_ui.py` verifies authenticated POST/CSRF selected/all
  queueing, bounded folder/review lists, worker/error visibility and exact JSON
  receipt/byte verification. Text-marker-only state cannot imply success.
- `browser/test_indexing.py` exercises real browser full/selected enqueue and
  cancellation; Linux continues through the real worker, verified STATUS and
  pending preview queue, with identical RAW and no inspection/usable assignment.

## WP-20a

- GR-03/04/05, AR-12/13/14: `tests/test_review_ui.py` covers read-only GET/preview,
  explicit version/proposal/hash/revision inspection, controlled combined parts,
  incompatible/inactive selection, personal attestation, rejection/new revision,
  corrupt bytes, failed publication and auth/CSRF. Metadata tests do not claim
  physical publication; existing WP-14 crash/recovery tests remain required.
- `browser/test_review.py` exercises actual PDF.js alongside candidate evidence,
  persistent correction/inspection and no preview auto-approval. Linux continues
  through real canonical queue/worker publication, confirmed combined assignments
  and unchanged RAW; existing WP-14 recovery protects the same publication path.

## WP-20b

- AR-13/GR-04: `tests/test_batch_review.py` verifies personal inspection, signed
  hash/version/proposal/revision/source state, stale/foreign/uninspected/changed
  selection rejection, POST/CSRF and entire-batch transaction rollback.
- `browser/test_batch_review.py` exercises real previous/next navigation, actual
  PDF inspection, persistent two-file selection and Linux durable batch publication
  with distinct no-clobber canonical destinations. Preview remains read-only.

## WP-21

- AR-15: `tests/test_library.py` verifies Unicode/casefold title and active alias
  interior matches, controlled arrangement/instrument/part/review/completeness
  filters, invalid filter/auth rejection, duplicate identities and pagination.
- AR-16/GR-05: independent required/optional/unknown expectation and confirmed/
  pending/missing material assertions; confirmed/withdrawn/missing/corrupt versions
  never become interchangeable, unreviewed candidates never usable; current manual
  correction takes precedence over historical recognition suggestions.
- `browser/test_library.py` exercises local-only live substring search, confirmed
  hash-verified edition, unknown completeness, independent expectation-template
  application and persisted incomplete/missing-part overview. No preferred edition,
  OCR, project generation or real NAS acceptance is claimed.

## WP-47a (software verification pending)

- OP-05: `tests/test_backup.py` uses migrated independent synthetic installations,
  actual worker copy/combined approval, rollback-journal/WAL Backup API, physical
  CLEAN/PROCESSED/STATUS/config/secret/DATA and protected assignment restoration.
  Service locks, competing writers, missing/corrupt/extra/manifest-only bundles,
  symlinks, live-root overlap, bounds and independent RAW mismatch are negative gates.
- `scripts/publication_smoke.py` extends the actual hardened non-root/no-network
  image test with full bundle capture and isolated physical restore. Linux CI
  evidence must pass; Windows fail-closed skips are not NAS acceptance.
