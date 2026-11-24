"""Isolated print renderer: physical geometry, vectors, rotations and source boundaries."""

from io import BytesIO

import pytest
from pypdf import PdfReader

from core.pdf import PdfError, Processor
from core.pdf.layout import A3, A4
from tests.pdf_fixtures import pdf


def origins(count, kind="MUSIC"):
    return [{"identity": "slot-1", "kind": kind, "pages": list(range(count))}]


@pytest.mark.parametrize("count", [1, 2, 3, 4, 5, 6, 7, 13, 40])
def test_print_render_arbitrary_a4_run_media_and_order(tmp_path, count):
    processor = Processor(tmp_path)
    source = pdf(sizes=(A4,) * count)
    output, result = processor.print_pdf(source, origins(count))
    reader = PdfReader(BytesIO(output))
    assert len(reader.pages) == (count + 1) // 2
    assert [p["page"] for sheet in result["plan"]["sheets"] for p in sheet["placements"]] == list(range(count))
    for index, page in enumerate(reader.pages):
        expected = A3 if index < count // 2 else A4
        assert tuple(page.mediabox)[2:] == pytest.approx(expected)
        assert f"Straße {index * 2}" in page.extract_text()
        if index < count // 2:
            assert f"Straße {index * 2 + 1}" in page.extract_text()
            assert page.get_contents().get_data().count(b" cm") >= 2


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
def test_print_normalizes_rotation_and_unit_without_original_mutation(tmp_path, rotation):
    sizes = A4 if rotation in (0, 180) else tuple(reversed(A4))
    sizes = tuple(v / 2 for v in sizes)
    source = pdf(sizes=(sizes, sizes), rotation=rotation, unit=2)
    output, result = Processor(tmp_path).print_pdf(source, origins(2))
    page = PdfReader(BytesIO(output)).pages[0]
    assert tuple(page.mediabox)[2:] == pytest.approx(A3)
    assert page.rotation == 0 and page.user_unit == 1
    assert result["plan"]["sheets"][0]["placements"][0]["source"]["rotation"] == rotation
    assert PdfReader(BytesIO(source)).pages[0].rotation == rotation


def test_print_native_a3_landscape_custom_crop_and_generated_pages_stay_whole(tmp_path):
    processor = Processor(tmp_path)
    source = pdf(sizes=(A3, tuple(reversed(A4)), (300, 200)))
    output, result = processor.print_pdf(source, origins(3))
    original, rendered = PdfReader(BytesIO(source)), PdfReader(BytesIO(output))
    assert len(rendered.pages) == 3
    for a, b in zip(original.pages, rendered.pages, strict=True):
        assert a.mediabox == b.mediabox and a.cropbox == b.cropbox
        assert a.get_contents().get_data() == b.get_contents().get_data()
    assert all(len(s["placements"]) == 1 for s in result["plan"]["sheets"])
    generated = pdf(sizes=(A4, A4))
    assert (
        len(PdfReader(BytesIO(processor.print_pdf(generated, origins(2, "CONTENTS"), mode="CONTENTS")[0])).pages) == 2
    )


def test_print_composition_manifest_keeps_piece_and_generated_boundaries(tmp_path):
    processor = Processor(tmp_path)
    music = pdf(sizes=(A4, A4, A4))
    pieces = [
        {"number": n, "title": "Synthetic", "state": state, "data": music if state == "MUSIC" else None}
        for n, state in [(1, "MUSIC"), (2, "RESERVE"), (3, "MISSING"), (4, "MUSIC")]
    ]
    data, composed = processor.compose(pieces, project="Synthetic", cover=True, with_manifest=True)
    output, result = processor.print_pdf(data, composed["origins"])
    assert len(PdfReader(BytesIO(output)).pages) == 7
    for sheet in result["plan"]["sheets"]:
        assert len({p["piece"] for p in sheet["placements"]}) == 1
        if sheet["placements"][0]["kind"] != "MUSIC":
            assert len(sheet["placements"]) == 1


def test_invalid_origin_inventory_and_visual_annotations_fail_closed(tmp_path):
    processor = Processor(tmp_path)
    for scope in (origins(1), [{"identity": "bad", "kind": "MUSIC", "pages": [1, 0]}]):
        with pytest.raises(PdfError):
            processor.print_pdf(pdf(sizes=(A4, A4)), scope)
    with pytest.raises(PdfError, match="UNSUPPORTED_ANNOTATION"):
        processor.print_pdf(pdf(annotation="/Text"), origins(1))


def test_paired_vector_visuals_match_left_right_originals_without_overlay(tmp_path):
    from tests.test_pdf import png

    processor = Processor(tmp_path)
    source = pdf(sizes=(A4, A4), text=False)
    printed, _ = processor.print_pdf(source, origins(2))
    # At a matching physical pixel scale compare the music's populated region,
    # avoiding fractional page-edge rounding in the renderer.
    width, height, pixels = png(processor.render(printed, dpi=127))
    first_width, first_height, first = png(processor.render(source, 0, dpi=127))
    second_width, second_height, second = png(processor.render(source, 1, dpi=127))

    def region(data, w, x):
        rows = []
        for y in range(1060, 1440):
            rows.append(data[y * (1 + w * 3) + 1 + x * 3 : y * (1 + w * 3) + 1 + (x + 450) * 3])
        return b"".join(rows)

    assert region(pixels, width, 0) == region(first, first_width, 0)
    assert region(pixels, width, 1050) == region(second, second_width, 0)
    # Both halves are pixel-identical at the exact 5-pixel/mm comparison scale.
    assert "Synthetic" not in PdfReader(BytesIO(printed)).pages[0].extract_text()
    assert second_width == first_width and second_height == first_height


def test_cropped_rotated_original_keeps_crop_and_geometry(tmp_path):
    source = pdf(sizes=((500, 600),), crop=(20, 40, 320, 440), rotation=90, unit=2)
    result, _ = Processor(tmp_path).print_pdf(source, origins(1))
    a, b = PdfReader(BytesIO(source)).pages[0], PdfReader(BytesIO(result)).pages[0]
    assert (
        a.mediabox == b.mediabox and a.cropbox == b.cropbox and a.rotation == b.rotation and a.user_unit == b.user_unit
    )


def test_print_preserves_transparency_groups_and_removes_active_content(tmp_path):
    from pypdf import PdfWriter
    from pypdf.generic import BooleanObject, DictionaryObject, NameObject

    source = PdfReader(BytesIO(pdf(sizes=(A4, A4), active=True)))
    writer = PdfWriter()
    for page in source.pages:
        page[NameObject("/Group")] = DictionaryObject(
            {NameObject("/S"): NameObject("/Transparency"), NameObject("/I"): BooleanObject(True)}
        )
        writer.add_page(page)
    buffer = BytesIO()
    writer.write(buffer)
    output, _ = Processor(tmp_path).print_pdf(buffer.getvalue(), origins(2))
    reader = PdfReader(BytesIO(output))
    page = reader.pages[0]
    assert "/OpenAction" not in reader.trailer["/Root"] and "/AA" not in page
    assert all(form.get_object()["/Group"]["/S"] == "/Transparency" for form in page["/Resources"]["/XObject"].values())


def test_renderer_rejects_transformed_geometry_overflow_before_publication(monkeypatch):
    from dataclasses import replace

    from core.pdf import printing
    from core.pdf.layout import LogicalPage, LogicalPiece, plan
    from core.pdf.structure import page_info
    from core.pdf.types import Limits

    reader = PdfReader(BytesIO(pdf(sizes=(A4, A4))))
    good = plan(
        (
            LogicalPiece(
                "piece",
                "MUSIC",
                tuple(LogicalPage("reading", i, page_info(page)) for i, page in enumerate(reader.pages)),
            ),
        )
    )
    sheet = good.sheets[0]
    placement = replace(sheet.placements[1], matrix=(1, 0, 0, 1, 2000, 0))
    invalid = replace(good, sheets=(replace(sheet, placements=(sheet.placements[0], placement)),))
    monkeypatch.setattr(printing, "plan", lambda *args, **kwargs: invalid)
    with pytest.raises(PdfError):
        printing.render(reader, origins(2), "FULL", Limits(), BytesIO())
