# Ensemble roles and mapping editor (WP-34)

This package extends the existing ProjectRole/EnsembleMapping/ProjectParticipant
graph; it does not create another project model or implement edition resolution.
The central resolver now consumes this component; see [RESOLUTION.md](RESOLUTION.md).
`ensemble_services.mapping_choice` is a reusable mapping component for the future
WP-32 resolver. A position-specific active mapping wins over the project mapping
for exactly the participant's saved instrument variant. Missing/invalid roles or
mappings return explicit status. No part-code, instrument-name or family inference,
automatic transposition, substitution or member-master fallback is performed.

German authenticated project editor provides role create/edit/deactivate/reactivate,
participant role assign/clear, mapping create/edit/explicit clear, project defaults
and position exceptions, and paginated mapping preview. Reserved/removed slots
cannot receive new exceptions. Every edit uses the existing project revision
compare-and-swap within a short write-first SQLite transaction. Foreign project
roles/positions/participants, inactive variants/parts, incompatible notation and
duplicate scope reject atomically. Active participants protect their role from
deactivation until explicitly unassigned. No hard deletion or implicit unassignment.

Mapping scope UUIDs stay stable and cannot be retargeted; editing changes the
selected playable part only. Explicit clear marks the mapping inactive and exposes
inheritance from the project default or missing status. Re-enable by deliberately
editing the retained mapping. Append-only EnsembleChange pins old/new parts/roles,
actor, project revision and bounded descriptive before/after evidence. Project
duplication retains active states, remaps project-local identities, and leaves
historical evidence with its original project. No original PDF/RAW/CLEAN/output
files or participant saved defaults/personal overrides are mutated by role edits.

Synthetic tests include four roles/seven participants with role 3 represented by
different exact instrument/key/clef parts, position preference and clear, missing
mapping, foreign scope/notation rejection, archive/stale revision denial, SQLite
nullable uniqueness, history, clone isolation, actual independent file-SQLite
writers/reopen and German browser editing. Container acceptance extends the
existing non-root/read-only-RAW/no-network scenario with role/participant/mapping
operations. Local software success is not private NAS/hardware acceptance.
