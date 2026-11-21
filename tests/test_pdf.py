"""Real isolated PDF processing with deterministic vector and one-bit scan inputs."""

import hashlib
import os
import struct
import zlib
from dataclasses import replace
from io import BytesIO

import pytest
from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, DecodedStreamObject, DictionaryObject, FloatObject, NameObject, NumberObject

from core.pdf import Limits, PdfError, Processor, Selection
from tests.pdf_fixtures import A3, A4, pdf


@pytest.fixture
def processor(tmp_path):
    return Processor(tmp_path)


def png(data):
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    width, height = struct.unpack(">II", data[16:24])
    offset, compressed = 8, b""
    while offset < len(data):
        size = struct.unpack(">I", data[offset : offset + 4])[0]
        kind, value = data[offset + 4 : offset + 8], data[offset + 8 : offset + 8 + size]
        assert zlib.crc32(kind + value) == struct.unpack(">I", data[offset + 8 + size : offset + 12 + size])[0]
        if kind == b"IDAT":
            compressed += value
        offset += 12 + size
    pixels = zlib.decompress(compressed)
    assert len(pixels) == height * (1 + width * 3)
    assert all(pixels[row * (1 + width * 3)] == 0 for row in range(height))
    return width, height, pixels


def test_vector_text_and_image_only_scan_are_distinct(processor):
    vector, scan = pdf(), pdf(text=False, scan=True)
    result = processor.inspect(vector, include_text=True)
    assert result.sha256 == hashlib.sha256(vector).hexdigest()
    assert result.text == ("Synthetic Übung Straße 0",)
    assert processor.extract_text(scan) == ("",)
    assert processor.inspect(vector).text is None
    assert png(processor.thumbnail(scan))[2].count(b"\0") > 200


@pytest.mark.parametrize("size,paper", [(A4, "A4"), (A3, "A3"), (A4[::-1], "A4"), ((481.89, 340.157), "CUSTOM")])
@pytest.mark.parametrize("rotation", [0, 90, 180, 270, -90, 450])
def test_physical_page_geometry_and_native_rendering(processor, size, paper, rotation):
    data = pdf(sizes=(size,), rotation=rotation)
    page = processor.inspect(data).pages[0]
    assert page.rotation == rotation % 360 and page.paper == paper
    expected = size[::-1] if rotation % 180 else size
    assert (page.width_points, page.height_points) == pytest.approx(expected)
    width, height, _ = png(processor.render(data, dpi=20))
    assert (width, height) == pytest.approx(tuple(value * 20 / 72 for value in expected), abs=1)


def test_cropbox_userunit_and_thumbnail_limit(processor):
    data = pdf(sizes=((500, 600),), crop=(20, 40, 320, 440), rotation=90, unit=2)
    page = processor.inspect(data).pages[0]
    assert page.media_box == (0, 0, 500, 600) and page.crop_box == (20, 40, 320, 440)
    assert page.user_unit == 2 and (page.width_points, page.height_points) == (800, 600)
    assert png(processor.render(data, dpi=72))[:2] == (800, 600)
    assert png(processor.thumbnail(data, max_edge=200))[:2] == (200, 150)


def test_effective_crop_intersects_media(processor):
    data = pdf(sizes=((200, 300),), crop=(-10, -20, 250, 350))
    assert processor.inspect(data).pages[0].crop_box == (0, 0, 200, 300)
    assert png(processor.render(data, dpi=72))[:2] == (200, 300)


def test_merge_preserves_vector_geometry_order_and_pixels(processor):
    data = pdf(sizes=(A4, A3, A4[::-1]), rotation=90, unit=1.25)
    before = hashlib.sha256(data).hexdigest()
    merged = processor.merge((Selection(data, (2, 1, 0, 1)),))
    info, original = processor.inspect(merged, include_text=True), processor.inspect(data, include_text=True)
    assert info.pages == tuple(original.pages[index] for index in (2, 1, 0, 1))
    assert info.text == tuple(original.text[index] for index in (2, 1, 0, 1))
    assert hashlib.sha256(data).hexdigest() == before
    reader = PdfReader(BytesIO(merged))
    assert all("/Font" in page["/Resources"] and "/XObject" not in page["/Resources"] for page in reader.pages)
    assert png(processor.render(merged, 0, dpi=40)) == png(processor.render(data, 2, dpi=40))


@pytest.mark.parametrize("data", [b"not a PDF synthetic-private", b"%PDF-1.7\ntruncated", b"%PDF-1.7\n%%EOF"])
def test_malformed_input_has_fixed_error_and_cleans_scratch(processor, data):
    with pytest.raises(PdfError) as error:
        processor.inspect(data)
    assert error.value.code == "INVALID_PDF" and "synthetic-private" not in str(error.value)
    assert list(processor.root.iterdir()) == []


def test_encrypted_input_is_not_silently_decrypted(processor):
    writer = PdfWriter()
    writer.add_blank_page(*A4)
    writer.encrypt("")  # Even an empty-password encrypted file requires explicit policy.
    stream = BytesIO()
    writer.write(stream)
    with pytest.raises(PdfError, match="ENCRYPTED_PDF"):
        processor.inspect(stream.getvalue())


@pytest.mark.parametrize("kwargs", [{"unit": 0}, {"unit": -1}, {"rotation": 45}, {"crop": (10, 10, 5, 5)}])
def test_invalid_geometry_is_rejected(processor, kwargs):
    with pytest.raises(PdfError, match="INVALID_PDF"):
        processor.inspect(pdf(**kwargs))


def test_size_page_pixel_text_and_aggregate_limits(tmp_path):
    data = pdf()
    small = Processor(tmp_path, limits=replace(Limits(), max_bytes=1024))
    with pytest.raises(PdfError, match="LIMIT_EXCEEDED"):
        small.inspect(data * 2)
    with pytest.raises(PdfError, match="LIMIT_EXCEEDED"):
        small.merge((Selection(data), Selection(data)))
    limited = Processor(tmp_path, limits=replace(Limits(), max_pages=1, max_pixels=100, max_text_chars=5))
    for operation in (
        lambda: limited.inspect(pdf(sizes=(A4, A4))),
        lambda: limited.render(data),
        lambda: limited.thumbnail(data),
        lambda: limited.extract_text(data),
        lambda: limited.inspect(pdf(sizes=((15000, 100),))),
        lambda: limited.merge((Selection(data), Selection(data))),
    ):
        with pytest.raises(PdfError, match="LIMIT_EXCEEDED"):
            operation()
    assert list(tmp_path.iterdir()) == []


def test_output_limit_is_enforced_during_merge_and_png_writes(tmp_path):
    limited = Processor(tmp_path, limits=replace(Limits(), max_output_bytes=1024))
    for operation in (lambda: limited.render(pdf()), lambda: limited.merge((Selection(pdf(sizes=(A4,) * 10)),))):
        with pytest.raises(PdfError, match="LIMIT_EXCEEDED"):
            operation()
    assert list(tmp_path.iterdir()) == []


def test_interactive_state_is_removed_without_changing_vector_content(processor):
    data = pdf(active=True, annotation="/Link")
    merged = processor.merge((Selection(data),))
    reader = PdfReader(BytesIO(merged))
    assert "/OpenAction" not in reader.trailer["/Root"] and "/AcroForm" not in reader.trailer["/Root"]
    assert "/AA" not in reader.pages[0] and "/Annots" not in reader.pages[0]
    assert processor.extract_text(merged) == processor.extract_text(data)


def test_visual_annotations_are_not_silently_lost(processor):
    with pytest.raises(PdfError, match="UNSUPPORTED_ANNOTATION"):
        processor.merge((Selection(pdf(annotation="/Ink")),))


def test_forms_are_not_rendered_as_if_missing_field_appearances_were_complete(processor):
    with pytest.raises(PdfError, match="UNSUPPORTED_ANNOTATION"):
        processor.render(pdf(annotation="/Widget"))


def test_invalid_page_and_contracts(processor):
    with pytest.raises(PdfError, match="INVALID_PAGE"):
        processor.render(pdf(), 1)
    with pytest.raises(PdfError, match="INVALID_PAGE"):
        processor.merge((Selection(pdf(), (1,)),))
    for operation in (
        lambda: processor.render(pdf(), -1),
        lambda: processor.render(pdf(), True),
        lambda: processor.render(pdf(), dpi=10000),
        lambda: processor.thumbnail(pdf(), max_edge=10000),
        lambda: processor.merge(()),
        lambda: processor.merge((Selection(pdf(), ()),)),
        lambda: Limits(max_pages=0),
        lambda: Limits(memory_bytes=True),
    ):
        with pytest.raises(ValueError):
            operation()
    with pytest.raises(TypeError):
        processor.inspect(bytearray(pdf()))


def test_cancellation_cleans_private_files(tmp_path):
    class Cancelled(Exception):
        pass

    calls = 0

    def checkpoint():
        nonlocal calls
        calls += 1
        if calls == 5:
            raise Cancelled

    processor = Processor(tmp_path, checkpoint=checkpoint)
    with pytest.raises(Cancelled):
        processor.render(pdf())
    assert calls == 5 and list(tmp_path.iterdir()) == []


def test_parse_worker_failure_and_timeout_are_sanitized(processor, monkeypatch):
    from core.processes import ProcessFailed, ProcessTimeout

    for exception, code in ((ProcessFailed, "PROCESS_FAILED"), (ProcessTimeout, "TIMEOUT")):

        def fail(*args, _error=exception, **kwargs):
            raise _error("synthetic-private-parser-message")

        monkeypatch.setattr("core.pdf.api.run_process", fail)
        with pytest.raises(PdfError) as error:
            processor.inspect(pdf())
        assert str(error.value) == code and list(processor.root.iterdir()) == []


@pytest.mark.skipif(os.name == "nt", reason="POSIX permissions; Windows scratch uses the caller's ACL")
def test_scratch_root_requires_private_canonical_directory(tmp_path):
    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    alias = tmp_path / "alias"
    alias.symlink_to(root, target_is_directory=True)
    with pytest.raises(ValueError, match="canonical"):
        Processor(alias)
    root.chmod(0o755)
    with pytest.raises(ValueError, match="private"):
        Processor(root)


def test_compressed_content_expansion_cannot_exhaust_parent(tmp_path):
    writer = PdfWriter()
    page = writer.add_page(PdfReader(BytesIO(pdf())).pages[0])
    content = DecodedStreamObject()
    content.set_data(b" " * (96 * 1024 * 1024))
    page[NameObject("/Contents")] = writer._add_object(content.flate_encode())
    stream = BytesIO()
    writer.write(stream)
    limited = Processor(tmp_path, limits=replace(Limits(), memory_bytes=67_108_864))
    with pytest.raises(PdfError) as error:
        limited.extract_text(stream.getvalue())
    assert error.value.code in {"LIMIT_EXCEEDED", "PROCESS_FAILED", "INVALID_PDF"}
    assert list(tmp_path.iterdir()) == []
    assert Processor(tmp_path).inspect(pdf()).pages[0].paper == "A4"


def test_type3_glyph_names_and_transparency_are_not_mistaken_for_actions(processor):
    writer = PdfWriter()
    page = writer.add_blank_page(*A4)
    glyph = DecodedStreamObject()
    glyph.set_data(b"600 0 d0 50 0 m 300 700 l 550 0 l 450 0 l 300 500 l 150 0 l h f")
    char_procs = DictionaryObject({NameObject(key): writer._add_object(glyph) for key in ("/A", "/S", "/AA")})
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type3"),
            NameObject("/FontBBox"): ArrayObject([NumberObject(n) for n in (0, 0, 600, 700)]),
            NameObject("/FontMatrix"): ArrayObject([FloatObject(n) for n in (0.001, 0, 0, 0.001, 0, 0)]),
            NameObject("/CharProcs"): char_procs,
            NameObject("/Encoding"): DictionaryObject(
                {NameObject("/Differences"): ArrayObject([NumberObject(65), NameObject("/A")])}
            ),
            NameObject("/FirstChar"): NumberObject(65),
            NameObject("/LastChar"): NumberObject(65),
            NameObject("/Widths"): ArrayObject([NumberObject(600)]),
            NameObject("/Resources"): DictionaryObject(),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
    )
    page[NameObject("/Group")] = DictionaryObject(
        {NameObject("/S"): NameObject("/Transparency"), NameObject("/CS"): NameObject("/DeviceRGB")}
    )
    content = DecodedStreamObject()
    content.set_data(b"BT /F1 50 Tf 100 500 Td (A) Tj ET")
    page[NameObject("/Contents")] = writer._add_object(content)
    stream = BytesIO()
    writer.write(stream)
    data = stream.getvalue()
    merged = processor.merge((Selection(data),))
    copied = PdfReader(BytesIO(merged)).pages[0]
    assert set(copied["/Resources"]["/Font"]["/F1"]["/CharProcs"]) == {"/A", "/S", "/AA"}
    assert copied["/Group"]["/S"] == "/Transparency"
    assert png(processor.render(data, dpi=72)) == png(processor.render(merged, dpi=72))


def test_native_build_has_no_javascript_or_xfa():
    import pypdfium2

    assert not {flag.casefold() for flag in pypdfium2.PDFIUM_INFO.flags} & {"v8", "xfa"}
