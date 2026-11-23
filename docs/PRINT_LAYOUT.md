# Regular print layout planner (WP-38a)

`core.pdf.layout.plan` is a pure deterministic function over frozen logical piece/
page/geometry records. It has no PDF parser, file/DB access, publication or printer
communication. Output is an immutable ordered sheet plan plus serializable manifest.
FULL, EXCERPT, ARCHIVE_NOTES and CONTENTS modes use the same boundary rules.

Each occurrence has its own unique identity; repeated arrangements at separate
positions are distinct pieces. Pages identify an immutable document and zero-based
index. Only consecutive pages in the same document AND MUSIC occurrence pair.
Generated COVER/CONTENTS/MISSING pages stay single; RESERVE has no pages and acts
as an explicit boundary. Every input page occurs once, in its original order.

Two physical A4 portrait pages become left/right A3 landscape (420 x 297 mm);
an odd remainder stays whole. Arbitrarily long runs are bounded by 1,000 input
pages/occurrences. Transformation matrices normalize the physical /Rotate and
/UserUnit coordinate system without fitting or musical modification. Native A3,
A4 landscape, custom and cropped pages retain original MediaBox/CropBox/rotation/
UserUnit as single sheets. No media sorting, cropping, splitting or fallback.

Pair eligibility deliberately uses exact A4 physical dimensions with 0.01-point
numeric authoring roundoff tolerance, not the broader 2-mm inspection label tolerance.
Near-A4 scans outside that bound remain single at original size with an explicit
warning; silently scaling them to nominal paper would change unapproved content.
Original cropped pages are never paired. Nonzero origins and normalized rotations
are supported. A raw portrait A4 rotated to landscape is kept single; a raw
landscape page rotated to physical A4 portrait can pair safely.

Manifest records source occurrence, kind, document/page, geometry, side, transform,
sheet media/physical dimensions and warnings. Invalid/nonfinite/inconsistent boxes,
out-of-media crop, invalid rotations/units, duplicate occurrence IDs, empty output
or exceeded bounds fail with fixed LayoutError codes. Unsupported output options
fail rather than enabling booklet, marchbook or A4-only fallback. Custom/landscape
PDF geometry is representable; actual printer medium/printable margins still require
later hardware acceptance. No physical printer capability is inferred.

Tests cover 1-6, 7/11/32/99-page runs, odd counts, A3/A4/custom/crop boundaries,
all rotations/units/origins, left/right corner geometry, generated/missing/reserve
pages, repeated occurrence identities, nonconsecutive documents, modes, deterministic
input preservation and invalid bounds. WP-38b supplies rendering/publication/preview;
this package publishes no artifacts and changes no reading PDF.
