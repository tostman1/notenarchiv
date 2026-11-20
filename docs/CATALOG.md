# Musical catalog and membership (WP-11/12)

These source features follow the published technical preview. They do not alter
the immutable 0.1.0-preview.1 image or deploy anything to the NAS. Use synthetic
master data until real-data use and a suitable release are explicitly approved.

## Identities and references

Work, arrangement, instrument variant, playable part, aliases, instrumentation
template and member have UUID identities. Equal work titles, arrangement labels,
template names and member names are permitted and never merged. Optional member
numbers are descriptive; they are not identity keys. The UI shows a short stable
identifier where equal labels otherwise cannot distinguish records.

Instrument variants have non-null name/family/transposition/clef components.
Unicode NFKC, collapsed whitespace and casefolded keys enforce canonical variant
and per-variant part-code uniqueness. Display spelling remains independent.
Notation is controlled; every part/member/expectation/alias assignment selects
an existing reference, never a replacement free-text label. Ensemble roles remain
separate project entities in WP-34; no role is automatically treated as a part.

Work aliases are unique within a work. Instrument aliases target exactly one
variant or playable part, enforced by a DB check and conditional unique indexes.
The same alias may refer to different identities. This package does not resolve
ambiguity or automatically assign notes; recognition remains a later package.

Each member has exactly one required, protected regular part, including inactive
members. Active members require an active part/variant. Their part/variant cannot
be deactivated until those memberships are reassigned or deactivated. Protected
FKs prevent referenced records from being deleted. Unreferenced records have an
explicit confirmed delete action; inactive records retain existing references.
Referenced variant identity components and a part's variant/code cannot be
silently reinterpreted. Create a new variant/part for a different musical
identity; descriptive labels and equivalent display casing remain editable.
Guests and saved project-specific defaults remain later project work.

## Expected instrumentation and templates

`expectations_defined=False` means unknown. An explicit defined list can be empty;
that differs from missing knowledge. Adding an expected part marks its list
defined. Removing its last row preserves the explicit empty definition. Returning
to unknown requires removing existing entries and explicitly clearing the flag.
Required and optional entries are distinct, unique arrangement/part pairs.

Applying a template copies its current entries, not a live relationship. Later
template changes do not mutate arrangements. Replacing an already defined list
requires explicit confirmation. All source parts/variants must be active; any
invalid entry rolls back the entire operation. Copying is bounded to 1000 entries.
No expectation list claims that music files are confirmed or available; archive
completeness and review remain distinct future functions.

## Write and UI boundary

Use `save_record`, `delete_record` and `apply_template` for domain writes.
Pre-validation provides errors; a short write-first SQLite transaction then
rechecks references against fresh DB state. Revision compare-and-swap prevents
stale forms overwriting newer edits. Changing child expectations invalidates an
open arrangement/template form. Unique/FK/alias constraints protect DB structure.

Only authenticated archivists can use the finite, whitelisted management screens.
Mutations require CSRF-protected POST; deletion requires confirmation. Search uses
normalized substrings, active/inactive filters and 25-row pages. Details show at
most 200 child entries with links to paginated lists. HTML is escaped and responses
are not cached. The German guide is [stammdaten.de.md](stammdaten.de.md).

Synthetic tests cover equal identities, Unicode/duplicate constraints, controlled
choices, required membership assignment, protected references/deactivation, stale
edits, atomic template copy/replace and bounds, unknown/empty expectations,
CSRF/XSS/pagination, actual migration/reopen persistence, and a full German browser
workflow. Actual NAS acceptance remains separate and unperformed.
