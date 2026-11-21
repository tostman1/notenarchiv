"""Copy selected page graphics without rasterization or interactive document state."""

from pypdf import PdfWriter
from pypdf.generic import ArrayObject, DictionaryObject, IndirectObject, NameObject

from core.pdf.types import PdfError

_PAGE_KEYS = {
    "/Type",
    "/Contents",
    "/Resources",
    "/MediaBox",
    "/CropBox",
    "/Rotate",
    "/UserUnit",
    "/Group",
    "/TrimBox",
    "/BleedBox",
    "/ArtBox",
}
_ACTION_TYPES = {
    "/JavaScript",
    "/Launch",
    "/URI",
    "/GoToR",
    "/GoToE",
    "/SubmitForm",
    "/ImportData",
    "/Rendition",
    "/Sound",
    "/Movie",
    "/SetOCGState",
    "/Hide",
    "/GoTo",
    "/Named",
    "/ResetForm",
}


def _scrub(value, seen, depth=0):
    if depth > 64 or len(seen) > 100_000:
        raise PdfError("LIMIT_EXCEEDED")
    if isinstance(value, IndirectObject):
        identity = (id(value.pdf), value.idnum, value.generation)
        if identity in seen:
            return
        seen.add(identity)
        value = value.get_object()
    if isinstance(value, DictionaryObject):
        action, kind = value.get("/S"), value.get("/Type")
        if (isinstance(action, NameObject) and action in _ACTION_TYPES) or (
            isinstance(kind, NameObject) and kind in {"/Filespec", "/EmbeddedFile"}
        ):
            value.clear()
            return
        for key in list(value):
            # A Type3 font may legitimately have a glyph named /A or /AA.
            # Interpret action keys only on the relevant PDF object types.
            if key in {"/AA", "/A", "/AF"} and isinstance(kind, NameObject) and kind in {"/Page", "/Annot", "/XObject"}:
                del value[key]
            else:
                _scrub(value.raw_get(key), seen, depth + 1)
    elif isinstance(value, ArrayObject):
        for child in value:
            _scrub(child, seen, depth + 1)


def _nonvisual_link(annotation):
    if annotation.get("/Subtype") != "/Link" or annotation.get("/AP"):
        return False
    style = annotation.get("/BS")
    if style is not None:
        return style.get_object().get("/W", 1) == 0
    border = annotation.get("/Border")
    if isinstance(border, IndirectObject):
        border = border.get_object()
    return isinstance(border, ArrayObject) and len(border) >= 3 and border[2] == 0


def merge(readers, selections, limits, output):
    writer, count = PdfWriter(), 0
    writer.pdf_header = "%PDF-1.7"
    for reader, selection in zip(readers, selections, strict=True):
        indices = range(len(reader.pages)) if selection is None else selection
        for index in indices:
            if not 0 <= index < len(reader.pages):
                raise PdfError("INVALID_PAGE")
            count += 1
            if count > limits.max_pages:
                raise PdfError("LIMIT_EXCEEDED")
            page = reader.pages[index]
            # Only provably invisible links can be discarded. Other annotations
            # may contain notation; never silently delete their appearance.
            annotations = page.get("/Annots", [])
            if isinstance(annotations, IndirectObject):
                annotations = annotations.get_object()
            if any(not _nonvisual_link(annotation.get_object()) for annotation in annotations):
                raise PdfError("UNSUPPORTED_ANNOTATION")
            copied = writer.add_page(page, excluded_keys=[key for key in page if key not in _PAGE_KEYS])
            _scrub(copied, set())
    writer.root_object.pop(NameObject("/AcroForm"), None)
    writer.write(output)
    writer.close()
    if output.tell() > limits.max_output_bytes:
        raise PdfError("LIMIT_EXCEEDED")
