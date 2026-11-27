# Local OCR: initial WP-24/25 increment

From a published version's review page, **Alle Seiten lokal mit OCR analysieren**
enqueues the existing OCR job. The normal single-heavy-worker runner processes
each source page, publishes progress and supports the existing cancellation UI.
Confirmed unchanged versions may be reanalysed without changing their approval,
musical assignments, inspection or historical exports. A derivative cannot be
silently treated as its original source.

Only verified byte-identical CLEAN publications are read. The processor stages
private copies, applies the exact original page geometry and renders at the
configured 100–300 DPI. OCR runs even when a text layer exists. Tesseract 5.5.2-r0
and German/English language packs are pinned in the Alpine container. LSTM-only
OCR uses at most two OpenMP threads, 384 MiB process memory and 60 seconds per
page. PDF processing retains its independent pixel/output/CPU limits. No text
is sent externally or included in subprocess logs.

The CLI uses the existing owned process runner, not pytesseract's second
subprocess lifecycle. This small implementation choice preserves the existing
process-tree containment, cancellation and uncertain-cleanup contract; it does
not replace the approved local Tesseract technology or queue. No Python OCR
dependency is necessary. Native Windows OCR runtime distribution is not supplied
by this increment; native Windows storage writes remain disabled.

Immutable page evidence retains original hash, source page, region bounds,
orientation/revision, recognized words and rendered-selection pixel boxes,
OCR confidence, PDF text, rule version and runtime/profile identity. Reanalysis
reuses matching committed page evidence; changed rules, source, geometry or
profile produce a different cache context. Worker metadata commits remain fenced.
The installed Alpine package database additionally binds the native dependency
closure to the cache runtime identity. Restart recovery under the existing
exclusive worker authority removes only recognized owned unmarked scratch files.
An active or unsafe abandoned scratch workspace blocks further OCR pending ownership review;
uncertain process termination never proves cancellation or permits cleanup.

The existing review selections allow manual correction/rejection/inspection;
OCR suggestions are never approval. The initial review displays page-level OCR
text and context. Selected-region launch, image evidence overlays, independent
multiple-work proposals, complete booklet continuation analysis and graphical
segmentation are subsequent increments, not delivered WP-26/56 acceptance.
WP-27 integrity and WP-28 representative DS224+ measurements remain separate.
The German manual plan must not infer recognition accuracy from synthetic tests.
