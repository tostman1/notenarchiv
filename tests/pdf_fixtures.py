"""Original deterministic vector/raster fixtures; no copied music/font programs.

Uses the PDF standard Base-14 Helvetica name, not a distributed font file.
Every path, pixel and text string below is authored solely for these tests.
"""

from io import BytesIO

from pypdf import PdfWriter
from pypdf.generic import (
    ArrayObject,
    DecodedStreamObject,
    DictionaryObject,
    FloatObject,
    NameObject,
    NumberObject,
)

A4 = (595.2756, 841.8898)
A3 = (841.8898, 1190.5512)


def pdf(*, sizes=(A4,), rotation=0, unit=1, crop=None, text=True, scan=False, annotation=None, active=False):
    writer = PdfWriter()
    for index, size in enumerate(sizes):
        page = writer.add_blank_page(*size)
        page[NameObject("/Rotate")] = NumberObject(rotation)
        page[NameObject("/UserUnit")] = FloatObject(unit)
        if crop is not None:
            page[NameObject("/CropBox")] = ArrayObject([FloatObject(value) for value in crop])
        resources = DictionaryObject()
        content = b"0 0 0 RG 2 w 30 30 m 200 100 l S\n"
        for y in range(120, 161, 10):
            content += f"30 {y} m 250 {y} l S\n".encode()
        if text:
            resources[NameObject("/Font")] = DictionaryObject(
                {
                    NameObject("/F1"): DictionaryObject(
                        {
                            NameObject("/Type"): NameObject("/Font"),
                            NameObject("/Subtype"): NameObject("/Type1"),
                            NameObject("/BaseFont"): NameObject("/Helvetica"),
                            NameObject("/Encoding"): NameObject("/WinAnsiEncoding"),
                        }
                    )
                }
            )
            content += b"BT /F1 24 Tf 30 200 Td (Synthetic \334bung Stra\337e " + str(index).encode() + b") Tj ET\n"
        if scan:
            image = DecodedStreamObject()
            image.set_data(bytes([0b10101010, 0xFF, 0xFF, 0xFF] * 32))
            image.update(
                {
                    NameObject("/Type"): NameObject("/XObject"),
                    NameObject("/Subtype"): NameObject("/Image"),
                    NameObject("/Width"): NumberObject(32),
                    NameObject("/Height"): NumberObject(32),
                    NameObject("/BitsPerComponent"): NumberObject(1),
                    NameObject("/ColorSpace"): NameObject("/DeviceGray"),
                }
            )
            resources[NameObject("/XObject")] = DictionaryObject(
                {NameObject("/Im0"): writer._add_object(image.flate_encode())}
            )
            content += b"q 300 0 0 300 30 300 cm /Im0 Do Q\n"
        stream = DecodedStreamObject()
        stream.set_data(content)
        page[NameObject("/Contents")] = writer._add_object(stream)
        page[NameObject("/Resources")] = resources
        if annotation:
            item = DictionaryObject({NameObject("/Subtype"): NameObject(annotation)})
            if annotation == "/Link":
                item[NameObject("/Border")] = ArrayObject([NumberObject(0)] * 3)
            page[NameObject("/Annots")] = ArrayObject([item])
        if active:
            action = DictionaryObject(
                {NameObject("/S"): NameObject("/JavaScript"), NameObject("/JS"): NameObject("/Synthetic")}
            )
            page[NameObject("/AA")] = action
            writer.root_object[NameObject("/OpenAction")] = action
    output = BytesIO()
    writer.write(output)
    return output.getvalue()
