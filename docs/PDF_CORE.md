# PDF foundation (WP-17)

`core.pdf.Processor` exposes inspection, per-page text extraction, PNG rendering,
thumbnails and ordered page copying/merging. It has no Django, OCR, archive
approval, publication, download route or print dependency. These source features
are not included in the immutable published 0.1.0-preview.1 image.

## Boundary and use

Create the processor with an existing private canonical local scratch directory,
normally an attempt directory under DATA. POSIX mode must deny group/other
access; on Windows the caller must supply a user-private ACL. Inputs are immutable
`bytes`, not request paths. Archive callers must authorize and read stable bounded
snapshots through their own safe-file service. This API cannot modify RAW/CLEAN.

```python
from core.pdf import Processor, Selection

processor = Processor(private_scratch, checkpoint=job_context.checkpoint)
info = processor.inspect(authorized_bytes, include_text=True)
preview_png = processor.thumbnail(authorized_bytes, page=0, max_edge=256)
reading_pdf = processor.merge((Selection(authorized_bytes, (0, 1)),))
```

Pages are zero-based; selection order and repetitions are explicit. `None`
selects all pages. Returned derivatives remain unapproved. The caller owns
persisted hashes, inspection/approval, job fencing and no-clobber publication.
Text is local evidence only; never log it or treat it as assignment authority.
An image-only scan returns empty text; OCR is a later explicit processing stage.

## Limits and failure behavior

Every untrusted pypdf/PDFium operation runs in an owned child process. Libraries
are not imported into the web/worker caller by this API. Existing process-tree
cleanup is reused for success, timeout and cancellation. POSIX sets address-space,
CPU, file-size, descriptor and core-dump limits before target imports. Windows
uses a waiting launcher, Job Object memory/CPU limits and kill-on-close containment.
Output writers enforce their byte cap on both platforms. This is resource/process
isolation, not a claim of a general hostile-code filesystem sandbox.

| Default per invocation | Limit |
| --- | --- |
| Aggregate immutable input | 100 MiB, at most 16 merge inputs |
| Input/output page count | 500, configurable up to 1000 |
| Rendered pixels | 30,000,000 per image; checked before allocation |
| Extracted text | 1,000,000 characters across all pages |
| Output | 100 MiB, checked on each write |
| Child memory / CPU / wall time | 384 MiB / 30 s / 60 s |
| Physical page edge | 14,400 points (200 inches) |
| pypdf decoded stream | min(32 MiB, memory limit / 8) |

`Limits` permits bounded reductions and selected bounded increases, never an
unlimited setting. pypdf also has bounded tree depth/entries and decoding work;
external JBIG2 decoder execution is disabled. Native image decoding is constrained
by the child memory/CPU limits. At most 100 MiB staged input, 100 MiB output and
8 MiB response metadata coexist, plus small request metadata. The caller must
provide bounded local storage and enforce the single-heavy-job contract; parallel
uncoordinated invocations are not a global disk quota. Temporary files are private
and removed on every normal exception/cancellation path. A host crash can leave
an attempt directory; recovery must remove only proven abandoned owned staging.

Malformed/encrypted/unsupported or excessive inputs fail with fixed `PdfError`
codes. Parser diagnostics/stdout/stderr and exception text are discarded. A killed
child reports `PROCESS_FAILED`; deadline expiry reports `TIMEOUT`. Unverified
process cleanup retains the framework's distinct cleanup failure instead of
claiming cancellation succeeded. No partial output is returned.

## Geometry, visuals and active content

Metadata records MediaBox, its effective intersection with CropBox, UserUnit and
normalized rotation. Physical point dimensions include UserUnit and rotation;
A4/A3 classification uses a 2 mm tolerance and never transforms the page.
PDFium reports canvas units without UserUnit. Rendering explicitly applies that
factor and cross-checks native geometry before bitmap allocation. PNG encoding
streams RGB rows using the standard library; no extra image dependency is needed.

Merging copies page content/resources, dimensions, rotation, UserUnit and
transparency groups; no page numbers, fitting, splitting or rasterization.
It deliberately starts a new document: no source catalog, forms, attachments,
outlines or document actions are copied. Page action fields and explicitly
borderless links without an appearance are excluded; typed action/attachment dictionaries in copied resources are
removed. Type3 glyph names such as `/A` are preserved. Visual annotations are
rejected for merge rather than silently deleting possibly musical content.
Preview rendering draws ordinary annotations but rejects Widgets/XFA because a
disabled form environment cannot guarantee their full appearance. Forms require
a later explicit safe flattening/visual acceptance workflow. This is not a
universal PDF malware sanitizer or support for every damaged PDF variant.

Synthetic tests cover vector/text and one-bit scans, German characters,
portrait/landscape A4/A3/custom sizes, rotations, CropBox/UserUnit, malformed and
encrypted inputs, every major limit, compressed expansion, cancellation cleanup,
active content, Type3/transparency and pixel-identical vector page copies.
Fixture paths/pixels/text and Type3 glyphs are original; Base-14 references do not
redistribute a font program. Native PDFium is built without V8/XFA. CI must run
these tests on Linux plus actual musllinux rendering in the hardened amd64 image.
Windows results do not establish NAS memory/performance/ACL acceptance.
