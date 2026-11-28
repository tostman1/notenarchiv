"""Bounded geometric text extraction for explicitly clipped logical pages."""

import json
from contextlib import closing

import pypdfium2 as pdfium

from core.pdf.types import PdfError


def extract(path, infos, limits, output):
    texts, total = [], 0
    with pdfium.PdfDocument(path) as document:
        for number in range(len(infos)):
            with closing(document[number]) as page, closing(page.get_textpage()) as textpage:
                # Reject oversized text before native allocation; clipped-out text
                # still counts toward this conservative resource bound.
                if textpage.count_chars() > limits.max_text_chars:
                    raise PdfError("LIMIT_EXCEEDED")
                # PDFium text bounds use unrotated PDF coordinates. get_size()
                # instead describes the displayed (rotated) dimensions.
                left, bottom, right, top = page.get_bbox()
                text = textpage.get_text_bounded(left=left, bottom=bottom, right=right, top=top)
                total += len(text)
                if total > limits.max_text_chars:
                    raise PdfError("LIMIT_EXCEEDED")
                texts.append(text)
    output.write(json.dumps(texts, ensure_ascii=False).encode("utf-8"))
