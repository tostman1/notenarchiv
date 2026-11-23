"""Isolated structural print renderer using the single deterministic sheet planner."""

from io import BytesIO

from pypdf import PageObject, PdfReader, PdfWriter
from pypdf.generic import ArrayObject, DecodedStreamObject, DictionaryObject, FloatObject, NameObject, NumberObject

from core.pdf.layout import EPSILON, LayoutError, LogicalPage, LogicalPiece, plan
from core.pdf.merging import merge
from core.pdf.structure import page_info
from core.pdf.types import PdfError


def render(reader, origins, mode, limits, output):
    if not isinstance(origins, list) or not 1 <= len(origins) <= 1000:
        raise PdfError("INVALID_PDF")
    indices, pieces = [], []
    for entry in origins:
        if set(entry) != {"identity", "kind", "pages"} or not isinstance(entry["pages"], list):
            raise PdfError("INVALID_PDF")
        pages = []
        for index in entry["pages"]:
            if type(index) is not int or not 0 <= index < len(reader.pages):
                raise PdfError("INVALID_PAGE")
            indices.append(index)
            pages.append(LogicalPage("reading", index, page_info(reader.pages[index])))
        pieces.append(LogicalPiece(entry["identity"], entry["kind"], tuple(pages)))
    if indices != list(range(len(reader.pages))):
        raise PdfError("INVALID_PDF")
    try:
        layout = plan(tuple(pieces), mode=mode, maximum_pages=limits.max_pages)
    except LayoutError:
        raise PdfError("INVALID_PDF") from None
    # Reuse the established annotation/action safe-copy primitive before transforms.
    safe = BytesIO()
    merge([reader], [None], limits, safe)
    clean = PdfReader(BytesIO(safe.getvalue()), strict=True)
    writer = PdfWriter()
    writer.pdf_header = "%PDF-1.7"
    try:
        for sheet in layout.sheets:
            if len(sheet.placements) == 1:
                writer.add_page(clean.pages[sheet.placements[0].page])
                continue
            target = PageObject.create_blank_page(width=sheet.width_points, height=sheet.height_points)
            resources, commands = DictionaryObject(), []
            for number, placement in enumerate(sheet.placements):
                a, b, c, d, e, f = placement.matrix
                box = placement.source.media_box
                corners = [(a * x + c * y + e, b * x + d * y + f) for x in (box[0], box[2]) for y in (box[1], box[3])]
                if any(
                    x < -EPSILON
                    or y < -EPSILON
                    or x > sheet.width_points + EPSILON
                    or y > sheet.height_points + EPSILON
                    for x, y in corners
                ):
                    raise PdfError("INVALID_PDF")
                page = clean.pages[placement.page]
                form = DecodedStreamObject()
                contents = page.get_contents()
                form.set_data(contents.get_data() if contents is not None else b"")
                form.update(
                    {
                        NameObject("/Type"): NameObject("/XObject"),
                        NameObject("/Subtype"): NameObject("/Form"),
                        NameObject("/FormType"): NumberObject(1),
                        NameObject("/BBox"): ArrayObject([FloatObject(v) for v in placement.source.media_box]),
                        NameObject("/Resources"): page.get("/Resources", DictionaryObject()).clone(writer),
                    }
                )
                if page.get("/Group"):
                    form[NameObject("/Group")] = page["/Group"].clone(writer)
                name = NameObject(f"/Source{number}")
                resources[name] = writer._add_object(form)
                matrix = " ".join(format(v, ".12g") for v in placement.matrix)
                commands.append(f"q {matrix} cm {name} Do Q\n".encode("ascii"))
            target[NameObject("/Resources")] = DictionaryObject({NameObject("/XObject"): resources})
            content = DecodedStreamObject()
            content.set_data(b"".join(commands))
            target[NameObject("/Contents")] = writer._add_object(content)
            writer.add_page(target)
        if len(writer.pages) != len(layout.sheets):
            raise PdfError("INVALID_PDF")
        for page, sheet in zip(writer.pages, layout.sheets, strict=True):
            info = page_info(page)
            physical = (
                (info.media_box[2] - info.media_box[0]) * info.user_unit,
                (info.media_box[3] - info.media_box[1]) * info.user_unit,
            )
            if info.rotation in (90, 270):
                physical = physical[::-1]
            if (
                info.media_box != sheet.media_box
                or info.crop_box != sheet.crop_box
                or abs(physical[0] - sheet.width_points) > EPSILON
                or abs(physical[1] - sheet.height_points) > EPSILON
            ):
                raise PdfError("INVALID_PDF")
        writer.write(output)
        if output.tell() > limits.max_output_bytes:
            raise PdfError("LIMIT_EXCEEDED")
        return layout.manifest()
    finally:
        writer.close()
        clean.close()
