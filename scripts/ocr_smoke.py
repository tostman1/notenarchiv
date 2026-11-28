"""Actual pinned container OCR; exclusively generated synthetic text fixtures."""

import io

from reportlab.lib.utils import ImageReader
from reportlab.pdfgen.canvas import Canvas

from core.ocr import Engine, Profile


def main():
    stream = io.BytesIO()
    canvas = Canvas(stream, pagesize=(420, 300))
    for title in ("Synthetic March", "Synthetic Polka"):
        canvas.setFont("Helvetica", 24)
        canvas.drawString(30, 250, title)
        canvas.drawString(30, 200, "Posaune II")
        canvas.showPage()
    canvas.save()
    engine = Engine(
        "/scratch",
        "/usr/bin/tesseract",
        "/usr/share/tessdata",
        profile=Profile(dpi=200),
        runtime_manifest="/lib/apk/db/installed",
    )
    # A true image-only page is built locally from generated synthetic music
    # headings. It must be recognized without any PDF text-layer assistance.
    image = engine.processor.render(stream.getvalue(), 0, dpi=200)
    scanned = io.BytesIO()
    scan_canvas = Canvas(scanned, pagesize=(420, 300))
    scan_canvas.drawImage(ImageReader(io.BytesIO(image)), 0, 0, width=420, height=300)
    scan_canvas.save()
    for page in range(2):
        result = engine.recognize_page(stream.getvalue(), page=page, rules="synthetic-smoke-v1")
        words = " ".join(word["text"] for word in result["words"])
        if "Synthetic" not in words or "Posaune" not in words or not result["text_layer"]:
            raise RuntimeError("Synthetic OCR smoke failed")
    result = engine.recognize_page(scanned.getvalue(), page=0, rules="synthetic-smoke-v1")
    words = " ".join(word["text"] for word in result["words"])
    if result["text_layer"] or "Synthetic" not in words or "Posaune" not in words:
        raise RuntimeError("Synthetic image-only OCR smoke failed")
    print("Synthetic text-layer and image-only OCR smoke passed")  # noqa: T201 - fixed synthetic result only


if __name__ == "__main__":
    main()
