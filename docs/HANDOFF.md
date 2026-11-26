# Development handoff — Codex to OpenCode

## Transfer status

- Repository: tostman1/notenarchiv
- Transfer branch: codex/windows-source-reader
- Comparison base: ab172f6f942d5de743aec21aa6f0222caaa9798e
- Implementation checkpoint: 6cd6ee4ed952e482614981afbd24e51222a76ab4
- Last integrated PR: #61
- Last verified Main CI: 45694893160
- Active work package: WP-06p
- Date: 2026-11-26

Codex execution was interrupted by token-budget exhaustion.
The Product Owner manually recovered, committed and pushed
the outstanding implementation.

This is a one-time manual recovery of an interrupted agent
session. It does not modify, waive or supersede any existing
governance, authorization, verification or handoff requirements.

All subsequent agent handoffs must follow the standard
procedure defined in AGENTS.md.

Handoff readiness does not imply implementation completion,
successful CI verification or merge readiness.

## Implemented work

The current checkpoint includes:

- Native read-only local NTFS source access.
- Native file identity and high-resolution timestamp metadata.
- Pinned directory traversal and reparse-point rejection.
- Read-only handles and conflicting-write protection.
- Shared cross-platform source-root selection.
- Archive and export filesystem consumer refactoring.
- Native Windows regression tests and CI coverage.

See docs/PROGRESS.md, docs/PORTABILITY.md and
tests/TRACEABILITY.md for implementation details.

## Verification status

Recorded Codex verification:

- 13 native Windows tests passed.
- 73 earlier targeted configuration/runtime/source tests passed.
- Ruff lint and formatting passed.
- Actionlint passed.
- Django system and migration-drift checks passed.

Full regression completion is unconfirmed.
Exact-head integration CI is unconfirmed.

The previous verified Main CI passed Foundation, Container,
Windows and changes. These results apply to the recorded Main
baseline, not to the new implementation.

The manual recovery introduced no additional implementation
changes beyond the preserved Codex working-tree checkpoint.

## Remaining work

- Review and complete the interrupted WP-06p increment.
- Complete outstanding regression and integration verification.
- Implement native writable Windows storage.
- Verify safe publication and recovery.
- Establish independent process-wide RAW write protection.
- Complete remaining applicable portability foundation gates.

Desktop packaging, installer development, network storage
support and physical acceptance retain their existing scope
and separate delivery gates.

## Preserved OCR prototype

- Recovery branch: recovery/codex-ocr-prototype
- Recovery SHA: 49477203ef9dfb7f93e9533b2334bcd563a4162b

The incomplete OCR prototype was recovered from a local stash
and pushed to a separate recovery branch.

It contains core/ocr.py, pyproject.toml and uv.lock changes.
The original local stash remains intact.

The prototype is incomplete, including the missing _region()
implementation. It is recovery material, not an approved or
verified feature delivery.

Do not merge the recovery branch directly. Assess reusable
portions against the current architecture, locked dependencies,
security boundaries and revised region-based requirements.

## Authorization and continuation

All existing governance and authorization rules remain unchanged.

The previously granted standing Product Owner development
authorization remains active within its documented boundaries.

DEC-13 and the expanded product requirements are integrated.

After completing the remaining portability foundation, continue
with WP-54/55 and the approved implementation roadmap.

Use moderately sized cohesive delivery packages, targeted tests,
deterministic development tools and the existing SHA-bound CI
waiter in accordance with the established repository process.

This handoff grants no additional authorization and does not
remove any required security, review, CI, release or physical
acceptance gate.

## Immediate next action

Apply the mandatory AGENTS.md takeover readiness gate to the
latest remote HEAD of codex/windows-source-reader.

Review all commits and changes since the recorded comparison
base, not merely the final transfer marker.

Recover the actual verification state and complete the
interrupted WP-06p implementation.

Then continue the approved roadmap autonomously within the
existing authorization boundaries.

No unresolved Product Owner decision is currently known.
