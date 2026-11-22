# Replacement and edition preference rules (WP-35)

Project/position ReplacementRule and edition-preference models are reused. Global
replacement rules have a singleton revision and protected desired/target parts.
All edits use a write-first revision barrier (global or project) and authenticated
German controlled references. Baseline replacements target a different playable
part of the same exact instrument/key/clef variant; no number-only inference,
automatic transposition, inferred cross-instrument compatibility or fallback chains.

Replacement selection is position > project > global, with exactly one explicit
target. `replacement_choice` is only this scope-selection component for WP-32,
not an independent assignment/edition resolver. Effective overlay graphs are
checked for cycles in affected project/position contexts; changing a global rule
or clearing a specific override cannot expose an inherited cycle. Invalid selected
rule is surfaced, not silently replaced by a less-specific rule. Rule contexts and
inventory have explicit bounds; model SQLite constraints protect unique scopes.

Project and position concrete edition preferences require exact arrangement/part
and confirmed hash-verified ArchiveAssignment, checked before the short DB write
and revision/eligibility rechecked inside. Position > project preference component
returns the selected scope, retaining withdrawn/corrupt invalid explicit references
until corrected. Personal exact edition wins later in WP-32. Archive-wide preference
is the existing WP-23a global edition level, not duplicated by a second model/UI.

Explicit clear keeps UUID and old target/edition while disabling the preference;
inheritance becomes deliberate, not deletion or hidden substitution. RuleChange
protects old/new parts/versions, actor and project/global revision. Project clones
copy project-scoped active rules/preferences with remapped local identities; globals
remain global, historical audit evidence stays with the originating scope. New
snapshots/output stale handling follows later packages; no existing PDF is mutated.

German editor covers global/project/position replacements, project/position concrete
editions, explicit reset, authentication/CSRF and stale conflicts. Reserved/removed
or foreign positions are denied; saved participant defaults and personal overrides
are untouched. Tests exercise overlay precedence/cycles, one-hop selection, invalid
references/notation/confirmed state, hash race, reset/history, clone isolation,
global SQLite writer race/reopen and actual browser forms. Hardened container rule
operations extend existing synthetic acceptance; no NAS/private-data acceptance.
