"""Clipped logical selections must not leak outside headings into OCR evidence."""

import io

import pytest
from reportlab.pdfgen.canvas import Canvas

from core.pdf import Processor
from core.pdf.types import Limits, PdfError


@pytest.mark.parametrize("orientation", [0, 90, 180, 270])
def test_only_selected_text_enters_region_evidence(tmp_path, orientation):
    tmp_path.chmod(0o700)
    stream = io.BytesIO()
    canvas = Canvas(stream, pagesize=(200, 200))
    canvas.drawString(20, 170, "Selected March")
    canvas.drawString(20, 30, "Outside Polka")
    canvas.save()
    processor = Processor(tmp_path)
    logical = processor.logical_pages(
        [stream.getvalue()], [{"input": 0, "page": 0, "bounds": [0, 100, 200, 200], "orientation": orientation}]
    )
    text = processor.extract_visible_text(logical)[0]
    assert "Selected March" in text
    assert "Outside" not in text and "Polka" not in text


def test_clipped_out_characters_still_count_toward_native_text_limit(tmp_path):
    tmp_path.chmod(0o700)
    stream = io.BytesIO()
    canvas = Canvas(stream, pagesize=(200, 200))
    canvas.drawString(20, 170, "Selected")
    canvas.drawString(20, 30, "Outside text exceeds the conservative native character limit")
    canvas.save()
    processor = Processor(tmp_path)
    logical = processor.logical_pages(
        [stream.getvalue()], [{"input": 0, "page": 0, "bounds": [0, 100, 200, 200], "orientation": 0}]
    )
    bounded = Processor(tmp_path, limits=Limits(max_text_chars=20))
    with pytest.raises(PdfError, match="LIMIT_EXCEEDED"):
        bounded.extract_visible_text(logical)


def test_visible_text_preserves_logical_page_order_and_total_limit(tmp_path):
    tmp_path.chmod(0o700)
    stream = io.BytesIO()
    canvas = Canvas(stream, pagesize=(200, 200))
    for title in ("First March", "Second Polka"):
        canvas.drawString(20, 170, title)
        canvas.showPage()
    canvas.save()
    processor = Processor(tmp_path)
    logical = processor.logical_pages(
        [stream.getvalue()],
        [{"input": 0, "page": page, "bounds": [0, 100, 200, 200], "orientation": 0} for page in (1, 0)],
    )
    texts = processor.extract_visible_text(logical)
    assert len(texts) == 2
    assert "Second Polka" in texts[0] and "First March" in texts[1]
    bounded = Processor(tmp_path, limits=Limits(max_text_chars=15))
    with pytest.raises(PdfError, match="LIMIT_EXCEEDED"):
        bounded.extract_visible_text(logical)
