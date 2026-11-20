# Agent handoff — latest snapshot

Update this file when the owner says **handoff / Übergabe**. On **takeover / Übernahme**, verify every statement against Git, source and checks. Procedures are defined in `AGENTS.md`; long-term work-package history belongs in `docs/PROGRESS.md`.

> Initial template — no handoff has been recorded here. Replace placeholders only with observed facts. The final commit cannot contain its own SHA; report the verified pushed SHA after the push.

## Git checkpoint

- Date (UTC): `<observed timestamp>`
- Outgoing agent: `<OpenCode | Codex | other>`
- Branch / upstream: `<branch> / <origin/branch or none>`
- Comparison base (full SHA): `<last shared checkpoint or feature-branch base>`
- Head before this handoff (full SHA): `<observed HEAD>`
- Intended transfer ref: `<origin/branch>`
- Working tree: `<clean | list staged, unstaged and untracked paths>`
- PR / merge status: `<URL and actual state | none>`

## Work status

- Work package / status: `<WP-XX — planned | in progress | implemented | verified | blocked>`
- Completed changes since comparison base: `<concise summary; reference commits/files>`
- Unfinished work / known defects: `<details or none>`
- Decisions pending from owner: `<details or none>`

## Verification

- Local checks: `<commands and observed results; or not run>`
- GitHub CI: `<run URL, result; or not checked>`
- NAS / hardware checks: `<observed results; or not run>`

## Continuation

- Next concrete action: `<one recommended step>`
- Transfer status: `<ready after verified push | not pushed | blocked>`
