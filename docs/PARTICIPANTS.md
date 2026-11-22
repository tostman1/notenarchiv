# Participants and saved project defaults (WP-31)

`participant_services` owns member selection, project-local guests, personal saved
project defaults and explicit member-default refresh. Every write shares the project
revision compare-and-swap and short write-first SQLite transaction. Whole selected
batches validate before effects; invalid/foreign/inactive/stale input rolls back.

One participant = protected member FK or project-local guest UUID, saved display
name/default playable Part, optional independent role, selection state and origin.
Addition copies member name/regular part/revision. No live FK fallback or signal
updates this saved default after master edits. Manual project default editing sets
origin MANUAL, modifies no member or personal position override. Refresh requires
the displayed exact member revision; names update only if explicitly checked.
Neither refresh nor selection/reset touches overrides, roles or the shared list.

Member selection page has bounded name/instrument-variant filter and 25-row pages.
Actor/project/revision-bound signed 15-minute scope token limits subset changes to
the shown page; other participants and guests remain unchanged. Select all means
all active regular members (not truncated filter/page); deselect all includes guests
but retains every participant UUID/default/override. Re-selection reuses old saved
defaults/IDs, never silently refreshes. Inactive members cannot be newly selected;
existing defaults/history remain. At most 500 active participants. Guests require
an active playable variant/part and never create permanent association members.

Append-only ParticipantChange records retain previous/selected part/name/selection,
actor, project/member revision. Project duplication remaps participant/guest IDs
while copying saved defaults, origin, roles and personal overrides. History remains
with its original project; copied state has its own duplication provenance.

German authenticated forms expose saved vs current member defaults, explicit refresh,
manual project default, subset/all/none/guest operations, and distinct ensemble role.
CSRF, escaped names, stale conflict and archival restrictions remain. The actual
matrix assignment resolver is WP-32 after WP-34/35; this package does not fabricate
effective generations, role mappings or personalized piece lists.

Synthetic acceptance covers subset/filter/scope/auth/CSRF, equal names, inactive
assignments, guest isolation, saved defaults across master edit, overrides untouched,
explicit refresh/name adoption, clone independence, limits and all-or-nothing failure.
Independent file-SQLite race/restart and real browser master-change/refresh are
exercised; actual hardened container participant/guest API smoke included. Private
NAS/member data, deployment/release and future resolver/generation remain separate.
