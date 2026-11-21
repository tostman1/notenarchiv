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
