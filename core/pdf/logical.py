"""Render explicitly selected physical-point rectangles as vector derivatives."""

from pypdf import PageObject, PdfWriter, Transformation
from pypdf.generic import NameObject, NumberObject, RectangleObject

from core.page_geometry import PageGeometry
from core.pdf.merging import _PAGE_KEYS, _nonvisual_link, _scrub
from core.pdf.structure import page_info
from core.pdf.types import PdfError


def logical_pages(readers, selections, limits, output):
    writer = PdfWriter()
    writer.pdf_header = "%PDF-1.7"
    if not 1 <= len(selections) <= limits.max_pages:
        raise PdfError("LIMIT_EXCEEDED")
    for selection in selections:
        source = readers[selection["input"]].pages[selection["page"]]
        info = page_info(source)
        effective = tuple(value * info.user_unit for value in info.crop_box)
        try:
            region = PageGeometry(effective, effective).region(selection["bounds"])
        except ValueError:
            raise PdfError("INVALID_PAGE") from None
        annotations = source.get("/Annots", [])
        if hasattr(annotations, "get_object"):
            annotations = annotations.get_object()
        if any(not _nonvisual_link(item.get_object()) for item in annotations):
            raise PdfError("UNSUPPORTED_ANNOTATION")
        # Clone first: repeated occurrences must not mutate their source or one another.
        temporary = PdfWriter()
        copied = temporary.add_page(source, excluded_keys=[key for key in source if key not in _PAGE_KEYS])
        _scrub(copied, set())
        x0, y0, x1, y1 = region.bounds
        copied.trimbox = RectangleObject(tuple(value / info.user_unit for value in region.bounds))
        copied[NameObject("/Rotate")] = NumberObject(0)
        copied[NameObject("/UserUnit")] = NumberObject(1)
        page = PageObject.create_blank_page(width=x1 - x0, height=y1 - y0)
        # merge_transformed_page emits an explicit clipping path at TrimBox.
        page.merge_transformed_page(copied, Transformation().scale(info.user_unit).translate(-x0, -y0), expand=False)
        page.rotate((info.rotation + selection["orientation"]) % 360)
        writer.add_page(page)
        temporary.close()
    writer.write(output)
    writer.close()
    if output.tell() > limits.max_output_bytes:
        raise PdfError("LIMIT_EXCEEDED")
