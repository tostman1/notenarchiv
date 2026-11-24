# Unified export library, targeted regeneration and stale status (WP-39)

Authenticated `/exports/` lists persisted artifacts plus all generation runs,
including failed/queued/partial runs with no downloadable artifact. Project/person/
kind/READING/PRINT filters and independent ten-row artifact/run pagination preserve
history. Display includes original project/archive metadata, person, kind/variant,
date, run/snapshot/hash, bytes/pages, completion, current-scope differences and exact
historical input availability. Same archivist rights apply to every authenticated
account; there is no per-user ownership or musician sharing model.

Classification is read-only and computed against immutable saved payloads:
- COMPLETE verified output bytes, missing/corrupt output and incomplete run are separate.
  An intact artifact whose batch contains another damaged file is labelled batch-
  unavailable, never advertised as a downloadable complete result.
- Current project differences do not revoke historically valid output or replace bytes.
- FULL compares the shared complete sequence; EXCERPT compares only requested original
  positions/numbers, so unrelated additions do not invalidate a selected excerpt.
- Only the artifact's participant is resolved with the existing central resolver.
  Relevant desired/effective part, edition/provenance, role/mapping/replacement,
  selected catalog/notation metadata, page/cover options and source-presence changes
  produce specific reasons. Changes to another participant leave unaffected output
  current. An archive preference cannot override a deliberate personal exact choice.
- ARCHIVE_NOTES are exact explicit selections, independent of mutable project defaults
  or archive preferences. Historical source eligibility/hash is checked separately.
- Immutable pinned input hash/state and actual artifact bytes are checked separately;
  an existing generated PDF remains available if a source needed for regeneration is
  lost. Unconfirmed/withdrawn input is never selected for a new run.

Classification is conservatively bounded to 60 seconds/512 MiB per page request,
with request-local file verification reuse. Exceeded/invalid comparisons are explicitly
shown as requiring targeted checking, never successful auto-update. No cached stale
flag mutates immutable artifact history. Metadata classifications are not a promise
that a historical layout can be reproduced byte-identically by future renderer versions.

**Targeted current regeneration** starts fresh preflight with the same person and
either the full current list or prior excerpt positions. The user reviews current
assignment/edition/missing choices and selects READING/PRINT. The chosen variant is
included in the preflight fingerprint; stale tokens cannot silently switch variants.
Contents uses its independent full shared-list authorization. Historical exact
reprints remain separate and preserve old numbers/editions. Nothing alters shared
positions or assignments as part of export. Every successful regeneration creates
a new snapshot/run/path/artifact; previous files remain unchanged.

Independent archive selection now offers generated READING or PRINT artifacts with
the same protected project-free snapshots/ordinal pins, bounded actual PDF/hash
inspection, actor/selection/variant-bound request replay and durable publication.
Selected documents preserve their confirmed combined-page content/order; no fake
project/person, no extra cover/contents. Existing direct original and ZIP downloads
remain unchanged. Archive print infrastructure from WP-38b is reused, not duplicated.

Completed selected artifacts can be downloaded as a bounded 20-file ZIP after CSRF,
run completeness/hash checks and private independently verified streaming staging.
Archive/EXPORT/STATUS/RAW roots cannot be used as scratch. Names are opaque artifact
UUIDs in the batch; original human-readable managed paths and person labels stay
visible independently. No partial/failed/uncertain output is exposed as complete.

No destructive retention: old referenced files/pins/snapshots/artifacts remain; only
proven abandoned staging is cleaned by existing dead-owner recovery. Download APIs
accept identities, not paths, and optional project scope must match. Auth, CSRF,
safe local PDF.js preview, no RAW writes and no printer communication remain.

Tests cover person-specific stale/default/override/edition/catalog/list/selection
changes, unaffected participants and explicit edition preservation, output vs input
corruption, read-only classification, targeted preflight/variant binding, login/CSRF/
cross-project identity/ZIP isolation, project-free ordered archive reading. Real Linux
targeted one-person/archive publication, process death/replay, old/new coexistence,
browser library/regeneration/ZIP/download and hardened network-disabled container
acceptance are mandatory. NAS filesystem/ACL/load/power-loss/visual/hardware gates
remain private and unperformed. No release/deployment/printing/OCR/extra WP included.
