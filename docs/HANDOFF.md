# Development handoff — Codex to OpenCode

## Transfer snapshot — 2026-11-26

- Repository `tostman1/notenarchiv`. Primary branch `codex/wp06p-clean-reconstruction`, upstream of the same name. Active PR #64 targets `main`.
- Comparison base and verified remote Main `5f99344e803b14f9a2ab77bbb298e4edf9810204`. Review the full primary and WP-54 diffs from that base. The final transfer commit supplies the mandatory marker and contains this snapshot. Verify its remote SHA from Git.
- Primary implementation checkpoint `b4a571d0b92e4a0a7b09f0fad52e4f417af68303`. The subsequent transfer commit changes documentation only. Its own CI is unverified at transfer. Bind review and merge decisions to the actual new head.

| Ref / PR | Exact checkpoint | Verification and integration |
| --- | --- | --- |
| `main` | `5f99344e803b14f9a2ab77bbb298e4edf9810204` | Merged #62, exact [Main CI 45834711455](https://github.com/tostman1/notenarchiv/actions/runs/45834711455) passed |
| `codex/windows-source-reader` / #62 | `97a9d9e8e67cc16d965bd133b91aedf874e6a6ab` | Exact [PR CI 45831584098](https://github.com/tostman1/notenarchiv/actions/runs/45831584098) passed, already integrated |
| `codex/wp54-source-pages` / #63 | `1cde38a59b51bbd2cbf55f0345a344d10e6a0d6d` | Exact [PR CI 45831729109](https://github.com/tostman1/notenarchiv/actions/runs/45831729109) passed, open draft against `main`, mergeable when inspected |
| `codex/wp06p-clean-reconstruction` / #64, pre-transfer | `b4a571d0b92e4a0a7b09f0fad52e4f417af68303` | Exact [PR CI 45833447636](https://github.com/tostman1/notenarchiv/actions/runs/45833447636) passed, open draft against `main`, mergeable before transfer |
| `recovery/codex-ocr-prototype` | `49477203ef9dfb7f93e9533b2334bcd563a4162b` | Preserved incomplete prototype. Reference only when OCR dependencies are satisfied |

All green results above cover Foundation, Container, and Windows on the listed SHA. #63 and #64 had no inline review threads at inspection. Both still require the applicable reviewed-head and integration gates. The two drafts have overlapping progress and traceability additions. Recheck the second against actual Main after the first merge, preserve both records, and verify the resulting head. No known unresolved CI failure applies to the verified checkpoints. The stale export cleanup fixture on an earlier #62 SHA was fixed in `97a9d9e`.

## Delivered and open

- **WP-06p in progress.** Main includes the read-only local NTFS adapter, bounded RAW preflight, shared publication/ownership boundaries, SHA-256 verification of physically separate parser inputs, and recovery protection for uncertain scratch. Reindexing detects and revalidates acknowledged CLEAN health without changing approval, path, receipts, or export-pinned revisions.
- **WP-06p POSIX restoration implemented and verified on #64's implementation SHA.** `restore_clean_copy` queues a missing acknowledged CLEAN path through the existing worker. It stages exact historical CLEAN or pinned RAW bytes, publishes without clobbering, and reconciles interruption using the retained intent and proof. Seven synthetic Ubuntu tests cover exact inputs, changed RAW, collision, process death before and after acknowledgement, and lost proof. Windows shared lifecycle/publication/ownership passed 57 tests. Ruff, migration drift, and whitespace checks passed. No physical power-loss or NAS acceptance was exercised.
- **WP-54 in progress.** #63 adds stable version-bound source-page UUIDs, an idempotent legacy backfill, and original CropBox capture for new indexing. Legacy original CropBoxes remain explicitly unknown. Synthetic migration, rollback/rebuild, geometry and indexing checks passed. Stable logical pages, immutable region revisions, ordered content references, the confirmed whole-file compatibility adapter, and full migration/restore and resolver parity remain open.
- **WP-55 planned.** Depends on WP-54 and its existing catalog/resolver prerequisites. WP-24 and subsequent approved packages follow their rebaselined dependencies in `IMPLEMENTATION_PLAN.md`.
- **Windows-specific acceptance open.** Keep native writes disabled. Verify independent OS RAW write denial with reader handles closed across the actual application roles using a dedicated non-admin, non-RAW-owner identity. Native writable staging/publication, recovery parity and supervised runtime acceptance still need evidence. Production provisioning, packaging, deployment and physical NAS acceptance retain their separate gates.

## OpenCode continuation

1. Pass the remote handoff marker gate on the primary branch before switching or editing. Review the full comparison ranges from the verified Main base and check exact current PR and CI evidence. The marker authorizes takeover only.
2. Complete the reviewed exact-head gates for #64 and #63. Start with the primary #64 if still applicable, verify exact Main CI after integration, then reconcile #63 with current Main and verify its head before merging. Continue after successful CI and integration. Routine approved implementation and reviewed green merges have standing authorization.
3. Complete WP-54 with region/logical-page and ordered content-reference identities, revision-bound confirmation, the legacy whole-file adapter, and interruption/backfill/restore and resolver parity. Then implement WP-55 collections, work hierarchy and content editions. Continue the roadmap by actual dependencies. Use Sol and Qwen for substantial delegated implementation and independent review where appropriate.
4. Apply DEC-15 as approved. Preserve independent OS RAW denial, physically separate verified processing copies, authoritative SQLite/history, no-clobber publication and evidence-preserving reconciliation. Keep outstanding Windows-specific acceptance separate from unaffected product development. Use deterministic tools and the documented SHA-bound CI waiter. No production deployment, real-data migration or production ACL changes are authorized.

## Local-only material

The three active continuation worktrees were clean before the transfer edits. No implementation is stranded locally. A pre-existing OCR stash `d36f3b5` remains in the Codex clone. The remotely available OCR recovery branch above preserves the incomplete prototype and dependency changes, so takeover does not depend on that stash. Do not blindly apply its old dependency/lock changes. Ignored local CI reports and synthetic test scratch are optional evidence and are excluded from transfer.
