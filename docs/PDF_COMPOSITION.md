# Reading PDF composition (WP-37a)

## Confirmed-content extension

EX-11/12 and PT-06–10 extend the same composer and isolated worker to confirmed
logical-page/region inputs. Preserve vector content, original printed numbering
and source lineage. Explicit page-preserving/region/repeat policies govern shared
pages. Content packing uses confirmed visual regions, without re-engraving or
arbitrary staff/system cuts. Legacy whole-file inputs and outputs remain valid.
New geometry/parity acceptance in the crosswalk is planned, not covered by the
existing composition tests alone.

`Processor.compose` accepts ordered explicit positions (`MUSIC`, `MISSING`,
`RESERVE`) with shared numbers/titles and immutable PDF byte inputs. The caller
must supply authorized snapshot inputs; this pure API performs no musical
resolution, acknowledgement, DB mutation or file publication.

The existing private PDF subprocess handles parsing and composition under bounded
memory/CPU/time/output limits. The same safe merge primitive copies music pages,
preserving MediaBox/CropBox/rotation/UserUnit and vector content streams. Invisible
links/actions are removed; unsupported visual annotations fail instead of silently
discarding musical notation. No piece numbers, titles or other overlay are added
to music pages. Native A3 stays whole. Reading pages are never paired; regular
print-sheet pairing remains the separate WP-38 planner/renderer, not this builder.

Generated pages: optional personal cover, German `Inhaltsverzeichnis` without page
numbers, visible reserve numbers and `Noten fehlen` placeholders. Reserve slots
produce no music/placeholder page. Contents use exactly the supplied shared order
and may span pages. Missing pages contain the title/person and acknowledgement
notice; no piece number is added to original music. Excerpt callers can disable
contents/cover; neither is inferred from a participant or part.

Generated dimensions default to A4 portrait and can use explicit bounded project
dimensions. Text wraps, including long words, without markup interpretation.
The bundled unmodified Bitstream Vera TrueType font supports German/Latin Unicode
and is embedded by ReportLab. Characters outside its coverage fail with
`UNSUPPORTED_TEXT`, not silent substitution. Broader-script font support is not
claimed. Font and dependency notices remain in the installed runtime wheel.

Bounds: 1,000 positions, ascending positive numbers, title/text at most 1,000
characters, existing 100 MiB aggregate input/output and PDF page limits. Composition
cannot silently omit invalid/unconfirmed states. Caller supplies exact MUSIC bytes;
archive eligibility/authorization remains mandatory in the snapshot service.

Tests in `test_pdf_composition.py` compare music content streams and geometry,
A3/A4/landscape/rotation/UserUnit/CropBox, multi-page positions, reserve/placeholder,
Unicode, optional cover, contents pagination, separate piece boundaries, generated
dimensions, literal markup and page limits. Existing PDF security/resource tests
remain required. There is no new browser route or downloadable output in WP-37a;
worker generation/publication is WP-37b. NAS/visual/hardware acceptance remains separate.
WP-37c adds `music=False` for contents-only authoring and explicit `CONTENTS`
logical entries (no musical bytes/placeholder). Music bytes in this mode are
rejected. Shared contents/reserve generation is reused; project metadata is included.
