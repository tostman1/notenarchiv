"""Parser implementation, imported only inside the resource-limited worker."""

import math
from dataclasses import asdict

from pypdf import PdfReader

from core.pdf.types import PageInfo, PdfError, SourcePageGeometry


def box(value):
    coordinates = tuple(float(item) for item in value)
    if len(coordinates) != 4 or not all(math.isfinite(item) for item in coordinates):
        raise PdfError("INVALID_PDF")
    if coordinates[2] <= coordinates[0] or coordinates[3] <= coordinates[1]:
        raise PdfError("INVALID_PDF")
    return coordinates


def page_info(page):
    media, crop = box(page.mediabox), box(page.cropbox)
    crop = box((max(media[0], crop[0]), max(media[1], crop[1]), min(media[2], crop[2]), min(media[3], crop[3])))
    unit = float(page.user_unit)
    raw_rotation = float(page.get("/Rotate", 0))
    if not math.isfinite(unit) or not 0 < unit <= 75000 or not math.isfinite(raw_rotation) or raw_rotation % 90:
        raise PdfError("INVALID_PDF")
    rotation = int(raw_rotation) % 360
    width, height = (crop[2] - crop[0]) * unit, (crop[3] - crop[1]) * unit
    if not 0 < width <= 14400 or not 0 < height <= 14400:
        raise PdfError("LIMIT_EXCEEDED")
    if rotation in (90, 270):
        width, height = height, width
    return PageInfo(media, crop, unit, rotation, width, height)


def source_page_geometry(page):
    """Opt-in original/effective retention inside the isolated parser boundary.

    Existing inspection and rendering keep using page_info, with unchanged
    validation/serialization. The geometry bridge may enforce its own limits.
    """
    info = page_info(page)
    return SourcePageGeometry(info, box(page.cropbox))


def open_pdf(path, limits):
    with path.open("rb") as stream:
        if stream.read(5) != b"%PDF-":
            raise PdfError("INVALID_PDF")
    reader = PdfReader(path, strict=True)
    if reader.is_encrypted:
        raise PdfError("ENCRYPTED_PDF")
    if not 1 <= len(reader.pages) <= limits.max_pages:
        raise PdfError("LIMIT_EXCEEDED")
    infos = [page_info(page) for page in reader.pages]
    return reader, infos


def inspect(reader, infos, limits, include_text, *, include_source_geometry=False):
    result = {"pages": [asdict(info) for info in infos]}
    if include_source_geometry:
        result["original_crop_boxes"] = [box(page.cropbox) for page in reader.pages]
    if include_text:
        texts, count = [], 0

        def visit(text, *_):
            nonlocal count
            count += len(text)
            if count > limits.max_text_chars:
                raise PdfError("LIMIT_EXCEEDED")

        for page in reader.pages:
            text = page.extract_text(visitor_text=visit)
            if sum(len(item) for item in texts) + len(text) > limits.max_text_chars:
                raise PdfError("LIMIT_EXCEEDED")
            texts.append(text)
        result["text"] = texts
    return result
