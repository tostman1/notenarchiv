"""Isolated reading-PDF authoring: generated pages never overlay music graphics."""

from io import BytesIO
from pathlib import Path

import reportlab
from pypdf import PdfReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

from core.pdf.merging import merge
from core.pdf.types import PdfError


def font():
    path = Path(reportlab.__file__).parent / "fonts" / "Vera.ttf"
    value = TTFont("ArchiveVera", str(path))
    pdfmetrics.registerFont(value)
    return value


def compose(readers, request, limits, output):
    selected, generated_readers = [], []
    face = font()
    width, height = request["page_size"]
    margin, leading = 36, 18

    def text(value):
        if any(ord(character) not in face.face.charToGlyph for character in value if not character.isspace()):
            raise PdfError("UNSUPPORTED_TEXT")
        return value

    def lines(value, available):
        # Character-level wrapping also bounds long words; no clipping/truncation.
        result, current = [], ""
        for character in text(value):
            if character == "\n" or (
                current and pdfmetrics.stringWidth(current + character, "ArchiveVera", 11) > available
            ):
                result.append(current)
                current = "" if character == "\n" else character
            else:
                current += character
        return [*result, current]

    def page_document(heading, entries):
        heading_lines = lines(heading, width - 2 * margin)
        if (len(heading_lines) + 2) * leading > height - 2 * margin:
            raise PdfError("LIMIT_EXCEEDED")
        data = BytesIO()
        canvas = Canvas(data, pagesize=(width, height), invariant=1, pageCompression=1)
        page_count = 1
        y = height - margin

        def start():
            nonlocal y
            canvas.setFont("ArchiveVera", 11)
            y = height - margin
            for line in heading_lines:
                canvas.drawString(margin, y, line)
                y -= leading
            y -= leading

        start()
        for entry in entries:
            for line in lines(entry, width - 2 * margin):
                if y < margin:
                    page_count += 1
                    if page_count > limits.max_pages:
                        raise PdfError("LIMIT_EXCEEDED")
                    canvas.showPage()
                    start()
                canvas.drawString(margin, y, line)
                y -= leading
        canvas.save()
        reader = PdfReader(BytesIO(data.getvalue()), strict=True)
        generated_readers.append(reader)
        selected.append(reader)

    try:
        if request["cover"]:
            page_document(
                request["project"],
                [
                    request["participant"],
                    "Projektdefault / Rolle: " + request["assignment"],
                    "Persönliche Stückzuordnungen können abweichen.",
                ],
            )
        if request["contents"]:
            entries = [
                f"{position['number']}. {position['title']}" + (" — Reserve" if position["state"] == "RESERVE" else "")
                for position in request["positions"]
            ]
            page_document(
                "Inhaltsverzeichnis", entries if request.get("music", True) else [request["project"], *entries]
            )
        for position in request["positions"] if request.get("music", True) else []:
            if position["state"] == "MUSIC":
                selected.append(readers[position["input"]])
            elif position["state"] == "MISSING":
                page_document(
                    "Noten fehlen",
                    [position["title"], request["participant"], "Diese fehlenden Noten wurden ausdrücklich bestätigt."],
                )
        if not selected:
            raise PdfError("INVALID_PDF")
        merge(selected, [None] * len(selected), limits, output)
    finally:
        for reader in generated_readers:
            reader.close()
