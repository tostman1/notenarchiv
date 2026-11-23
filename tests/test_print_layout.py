"""Pure deterministic media planning, explicit occurrence boundaries and no fitting."""

from dataclasses import replace

import pytest

from core.pdf.layout import A3, A4, LayoutError, LogicalPage, LogicalPiece, plan
from core.pdf.types import PageInfo


def geometry(width=A4[0], height=A4[1], rotation=0, unit=1, origin=(0, 0)):
    box = (origin[0], origin[1], origin[0] + width / unit, origin[1] + height / unit)
    physical = (height, width) if rotation in (90, 270) else (width, height)
    return PageInfo(box, box, unit, rotation, *physical)


def piece(identity="slot-1", count=1, info=None, kind="MUSIC"):
    return LogicalPiece(identity, kind, tuple(LogicalPage("file-1", i, info or geometry()) for i in range(count)))


@pytest.mark.parametrize("count", [1, 2, 3, 4, 5, 6, 7, 11, 32, 99])
def test_arbitrary_a4_runs_have_correct_sheets_sizes_and_reading_order(count):
    result = plan((piece(count=count),))
    assert len(result.sheets) == (count + 1) // 2
    assert [p.page for s in result.sheets for p in s.placements] == list(range(count))
    for sheet in result.sheets:
        assert (sheet.width_points, sheet.height_points) == (A3 if len(sheet.placements) == 2 else A4)
    if count % 2:
        assert result.sheets[-1].placements[0].side == "WHOLE"


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
def test_pair_rotation_userunit_origin_transforms_fill_correct_left_right_cells(rotation):
    width, height = A4 if rotation in (0, 180) else tuple(reversed(A4))
    info = geometry(width, height, rotation, unit=2, origin=(13, -7))
    sheet = plan((piece(count=2, info=info),)).sheets[0]
    assert len(sheet.placements) == 2 and sheet.media_box == (0, 0, *A3)
    for placement, offset in zip(sheet.placements, (0, A4[0]), strict=True):
        a, b, c, d, e, f = placement.matrix
        box = info.media_box
        points = [(a * x + c * y + e, b * x + d * y + f) for x in (box[0], box[2]) for y in (box[1], box[3])]
        assert min(x for x, y in points) == pytest.approx(offset)
        assert max(x for x, y in points) == pytest.approx(offset + A4[0])
        assert min(y for x, y in points) == pytest.approx(0)
        assert max(y for x, y in points) == pytest.approx(A4[1])


def test_native_a3_landscape_custom_and_crop_break_pairing_without_geometry_loss():
    infos = [
        geometry(),
        geometry(A3[0], A3[1]),
        geometry(),
        geometry(*reversed(A4)),
        geometry(340, 220),
        geometry(),
        replace(
            geometry(), crop_box=(20, 20, A4[0] - 20, A4[1] - 20), width_points=A4[0] - 40, height_points=A4[1] - 40
        ),
        geometry(),
    ]
    pages = tuple(LogicalPage("file", i, info) for i, info in enumerate(infos))
    result = plan((LogicalPiece("position", "MUSIC", pages),))
    assert len(result.sheets) == len(infos)
    for sheet, info in zip(result.sheets, infos, strict=True):
        assert sheet.media_box == info.media_box and sheet.crop_box == info.crop_box
        assert len(sheet.placements) == 1 and sheet.placements[0].matrix == (1, 0, 0, 1, 0, 0)


def test_repeated_arrangements_generated_missing_reserve_and_positions_never_pair():
    pieces = (
        piece("cover", kind="COVER"),
        piece("contents", count=2, kind="CONTENTS"),
        piece("position-1"),
        LogicalPiece("reserve", "RESERVE"),
        piece("position-3"),
        piece("missing", count=2, kind="MISSING"),
        piece("repeat-arrangement-position-5", count=3),
    )
    result = plan(pieces)
    assert len(result.sheets) == 9
    assert [p.piece for s in result.sheets for p in s.placements] == [p.identity for p in pieces for _ in p.pages]
    assert all(len(s.placements) == 1 for s in result.sheets[:-2])
    assert len(result.sheets[-2].placements) == 2


@pytest.mark.parametrize("mode", ["FULL", "EXCERPT", "ARCHIVE_NOTES", "CONTENTS"])
def test_output_modes_are_deterministic_and_input_unchanged(mode):
    pieces = (piece(kind="CONTENTS" if mode == "CONTENTS" else "MUSIC", count=3),)
    original = repr(pieces)
    assert plan(pieces, mode=mode).manifest() == plan(pieces, mode=mode).manifest()
    assert repr(pieces) == original


def test_nonconsecutive_or_distinct_document_pages_cannot_pair():
    pages = (
        LogicalPage("file-a", 0, geometry()),
        LogicalPage("file-a", 2, geometry()),
        LogicalPage("file-b", 3, geometry()),
    )
    assert len(plan((LogicalPiece("piece", "MUSIC", pages),)).sheets) == 3


def test_near_a4_oversized_pages_stay_whole_without_silent_scaling():
    result = plan((piece(count=2, info=geometry(A4[0] + 1, A4[1] + 1)),))
    assert len(result.sheets) == 2
    assert "NONSTANDARD_A4_PRESERVED_UNPAIRED" in result.sheets[0].warnings


@pytest.mark.parametrize(
    "info",
    [
        replace(geometry(), width_points=3),
        replace(geometry(), user_unit=0),
        replace(geometry(), rotation=45),
        replace(geometry(), media_box=(0, 0, float("nan"), 20)),
        replace(geometry(), crop_box=(-1, 0, *A4)),
    ],
)
def test_invalid_geometry_fails_closed(info):
    with pytest.raises(LayoutError):
        plan((piece(info=info),))


def test_invalid_empty_duplicate_boundaries_and_limits_fail_closed():
    for pieces in ((), (piece("same"), piece("same")), (LogicalPiece("reserve", "RESERVE"),)):
        with pytest.raises(LayoutError):
            plan(pieces)
    with pytest.raises(LayoutError):
        plan((piece(count=3),), maximum_pages=2)
    with pytest.raises(LayoutError):
        plan((piece(),), mode="CONTENTS")


def test_real_pdf_inspection_feeds_media_plan_without_modifying_original_bytes(tmp_path):
    from core.pdf import Processor
    from tests.pdf_fixtures import pdf

    data = pdf(sizes=(A4, A4, A3, tuple(reversed(A4))))
    original = bytes(data)
    info = Processor(tmp_path).inspect(data)
    pages = tuple(LogicalPage("synthetic-pinned-document", i, page) for i, page in enumerate(info.pages))
    result = plan((LogicalPiece("synthetic-position", "MUSIC", pages),), mode="EXCERPT")
    assert len(result.sheets) == 3
    assert result.sheets[0].media_box == (0, 0, *A3)
    assert result.sheets[1].media_box == info.pages[2].media_box
    assert result.sheets[2].media_box == info.pages[3].media_box
    assert data == original
