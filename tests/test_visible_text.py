"""Clipped logical selections must not leak outside headings into OCR evidence."""

import io

import pytest
from reportlab.pdfgen.canvas import Canvas

from core.pdf import Processor


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
