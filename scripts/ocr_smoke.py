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
    selected = engine.recognize_page(scanned.getvalue(), page=0, bounds=[0, 225, 420, 300], rules="synthetic-smoke-v1")
    selected_words = " ".join(word["text"] for word in selected["words"])
    if "Synthetic" not in selected_words or "Posaune" in selected_words:
        raise RuntimeError("Synthetic selected-region OCR smoke failed")
    if selected["cache_key"] == result["cache_key"]:
        raise RuntimeError("Synthetic selected-region cache isolation failed")
    digital_selection = engine.recognize_page(
        stream.getvalue(), page=0, bounds=[0, 225, 420, 300], rules="synthetic-smoke-v1"
    )
    if "Synthetic" not in digital_selection["text_layer"] or "Posaune" in digital_selection["text_layer"]:
        raise RuntimeError("Synthetic selected-region text-layer isolation failed")
    compound = io.BytesIO()
    compound_canvas = Canvas(compound, pagesize=(420, 300))
    compound_canvas.setFont("Helvetica", 24)
    compound_canvas.drawString(30, 250, "Synthetic March")
    compound_canvas.drawString(30, 100, "Synthetic Polka")
    compound_canvas.save()
    compound_image = engine.processor.render(compound.getvalue(), 0, dpi=200)
    compound_scan = io.BytesIO()
    compound_scan_canvas = Canvas(compound_scan, pagesize=(420, 300))
    compound_scan_canvas.drawImage(ImageReader(io.BytesIO(compound_image)), 0, 0, width=420, height=300)
    compound_scan_canvas.save()
    evidence = engine.recognize_page(compound_scan.getvalue(), page=0, rules="synthetic-smoke-v1")
    lines = {}
    for word in evidence["words"]:
        lines.setdefault(tuple(word["line"]), []).append(word)
    recognized = [(" ".join(word["text"] for word in words), words[0]["box"][1]) for words in lines.values()]
    titles = [(text, top) for text, top in recognized if text in ("Synthetic March", "Synthetic Polka")]
    if evidence["text_layer"] or [text for text, _ in titles] != ["Synthetic March", "Synthetic Polka"]:
        raise RuntimeError("Synthetic image-only compound heading smoke failed")
    if titles[0][1] >= titles[1][1]:
        raise RuntimeError("Synthetic compound heading location order failed")
    print("Synthetic text-layer, image-only and selected-region OCR smoke passed")  # noqa: T201


if __name__ == "__main__":
    main()
