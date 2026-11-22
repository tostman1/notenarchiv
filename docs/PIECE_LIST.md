# Shared piece list (WP-30)

One ProjectPosition list for every project, never participant-scoped. Dense order
includes explicit null-arrangement reserves. UI contents numbering derives from
the current sorted slot sequence; no independent editable piece-number field and
no PDF stamping. Repeated arrangements have independent UUIDs.

`list_services` is the only normal position mutation API. It obtains the existing
project revision write-first SQLite transaction, validates all slot IDs/order/size,
and applies insert/move/reorder/remove/fill/replace atomically. Unique order uses
temporary positive offset followed by bulk final values. Missing/duplicate/foreign
IDs, inactive arrangements, archived projects, stale requests and >1000 active
positions reject with full rollback. No `select_for_update` reliance.

Drag/drop previews ordering and renumbers the DOM, not the DB; explicit save
submits every slot UUID and expected project revision. Keyboard-accessible numeric
move controls and ordinary POST forms work without JavaScript. Live searchable
library uses the same title/alias substring engine as the archive, with optional
filters and pagination. Selection never turns pending notes into confirmed music.

Filling/replacing retains position UUID and order. Existing arrangement replacement
requires acknowledgement. On changed arrangement all position overrides/edition
preferences are marked needs_revalidation; pinned references are retained for
historical integrity and never automatically adopted for the replacement. Future
central assignment engine must enforce this marker. Removal is explicit inactive
state with null order, retains references and marks those choices invalid. Position
change rows protect previous/selected arrangement, order, state, actor and revision;
no destructive position deletion. Reordering moves reserves as slots, not fixed
number labels (DEC-03/D-03). Current contents are shown before generation, which
remains a later package.

Tests cover 3→1, independent repeated UUIDs, reserve numbering/fill/removal, same-slot
replacement/acknowledgement, unchanged personal numbering, invalid/stale sets,
mid-order rollback, append-only references, limits, no personal-list model and real
file-SQLite competing writers/restart. Browser exercises drag/drop persistence,
live search and reserve fill. Hardened image smoke validates shared-list edits.
NAS and generated-folder/print acceptance are not claimed by this software package.
