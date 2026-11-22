# Preferred archive editions (WP-23a)

`PreferredEdition` is one protected UUID scope per exact arrangement/playable part.
The part's InstrumentVariant includes transposition and clef; an equal voice number
or instrument name does not establish compatibility. The selected ArchiveAssignment
is protected and version-specific. A combined PDF can support separate preferences
for its several explicitly confirmed assignments, never duplicate music implicitly.

Preference changes serialize via arrangement revision compare-and-swap in short
write-first SQLite transactions. Verify actual PDF bytes before the transaction,
then recheck usable assignment and exact archive revision after the write barrier.
Withdrawn/pending/inactive/foreign/corrupt selections fail. Clearing explicitly
keeps the preference UUID, with a null selection; append-only protected change rows
retain previous/selected assignment IDs, actor, time and resulting revision. Even
an inactive part can have its obsolete preference explicitly cleared.

`edition_services.resolve` is the reusable edition component for the future shared
project resolver, not a second project assignment engine. It returns availability
and provenance: explicit version, archive preference, sole compatible confirmed
version, missing, ambiguous or unavailable. Invalid explicit choices/preferences
never fall back. No transposition/substitution is inferred. Actual-byte verification
is required for any returned assignment; generation must additionally pin and
revalidate those immutable inputs at its own future snapshot/publication boundaries.

German authenticated UI lists paginated version identities, notation/transposition,
confirmation/withdrawal and hash status, preview, explicit version check, prefer and
reset POST controls with CSRF and optimistic conflicts. GET never changes preference.
The explicit version URL is a read-only check, not a project override entity. Project
edition hierarchy, output stale markers and snapshots follow their own packages:
no project/output exists at this milestone, no old output is rewritten or fabricated.

Tests cover multi-version ambiguity, incompatible/pending rejection, derivative
approval, damaged/withdrawn selected versions, explicit selection after preference
changes, reset, protections, stale write rollback, actual independent file-SQLite
writer races/reopen and local browser persistence. No NAS/private data is involved.
