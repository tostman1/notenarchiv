"""Bounded native rendering and streaming RGB PNG encoding; no forms or scripts."""

import math
import struct
import zlib
from contextlib import closing

import pypdfium2 as pdfium

from core.pdf.types import PdfError


def _chunk(stream, kind, data):
    stream.write(struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data)))


def _png(bitmap, stream, limit):
    stream.write(b"\x89PNG\r\n\x1a\n")
    _chunk(stream, b"IHDR", struct.pack(">IIBBBBB", bitmap.width, bitmap.height, 8, 2, 0, 0, 0))
    compressor = zlib.compressobj(6)
    buffer = memoryview(bitmap.buffer).cast("B")
    for row in range(bitmap.height):
        start = row * bitmap.stride
        encoded = compressor.compress(b"\0" + buffer[start : start + bitmap.width * 3].tobytes())
        if encoded:
            _chunk(stream, b"IDAT", encoded)
        if stream.tell() > limit:
            raise PdfError("LIMIT_EXCEEDED")
    _chunk(stream, b"IDAT", compressor.flush())
    _chunk(stream, b"IEND", b"")
    if stream.tell() > limit:
        raise PdfError("LIMIT_EXCEEDED")


def render(path, info, request, limits, output):
    if request.get("max_edge"):
        scale = request["max_edge"] / max(info.width_points, info.height_points)
    else:
        scale = request["dpi"] / 72
    width, height = math.ceil(info.width_points * scale), math.ceil(info.height_points * scale)
    if not width or not height or width * height > limits.max_pixels:
        raise PdfError("LIMIT_EXCEEDED")
    with pdfium.PdfDocument(path) as document, closing(document[request["page"]]) as page:
        native_width, native_height = page.get_size()
        if (
            not all(math.isfinite(value) and value > 0 for value in (native_width, native_height))
            or abs(native_width * info.user_unit - info.width_points) > 0.1
            or abs(native_height * info.user_unit - info.height_points) > 0.1
        ):
            raise PdfError("INVALID_PDF")
        # PDFium reports canvas units, ignoring /UserUnit. Account for it
        # explicitly; perform all allocation checks before calling render.
        native_scale = scale * info.user_unit
        if math.ceil(native_width * native_scale) * math.ceil(native_height * native_scale) > limits.max_pixels:
            raise PdfError("LIMIT_EXCEEDED")
        with closing(
            page.render(
                scale=native_scale,
                force_bitmap_format=pdfium.raw.FPDFBitmap_BGR,
                rev_byteorder=True,
                draw_annots=True,
                may_draw_forms=False,
            )
        ) as bitmap:
            if bitmap.width * bitmap.height > limits.max_pixels:
                raise PdfError("LIMIT_EXCEEDED")
            _png(bitmap, output, limits.max_output_bytes)
