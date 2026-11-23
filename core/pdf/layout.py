"""Pure regular print-sheet planning; no parsers, I/O, Django or publication."""

import math
from dataclasses import asdict, dataclass

from core.pdf.types import PageInfo

MM = 72 / 25.4
A4 = (210 * MM, 297 * MM)
A3 = (420 * MM, 297 * MM)
EPSILON = 0.01  # Numeric PDF authoring roundoff only, not permission to scale.
MODES = {"FULL", "EXCERPT", "ARCHIVE_NOTES", "CONTENTS"}
KINDS = {"MUSIC", "COVER", "CONTENTS", "MISSING", "RESERVE"}


class LayoutError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class LogicalPage:
    document: str
    index: int
    geometry: PageInfo


@dataclass(frozen=True)
class LogicalPiece:
    identity: str  # Position/occurrence identity, never just arrangement identity.
    kind: str
    pages: tuple[LogicalPage, ...] = ()


@dataclass(frozen=True)
class Placement:
    piece: str
    kind: str
    document: str
    page: int
    side: str
    matrix: tuple[float, float, float, float, float, float]
    source: PageInfo


@dataclass(frozen=True)
class Sheet:
    media_box: tuple[float, float, float, float]
    crop_box: tuple[float, float, float, float]
    rotation: int
    user_unit: float
    width_points: float
    height_points: float
    placements: tuple[Placement, ...]
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class PrintPlan:
    mode: str
    pieces: tuple[LogicalPiece, ...]
    sheets: tuple[Sheet, ...]
    schema: int = 1

    def manifest(self):
        return asdict(self)


def _dimensions(box, unit, rotation):
    width, height = (box[2] - box[0]) * unit, (box[3] - box[1]) * unit
    return (height, width) if rotation in (90, 270) else (width, height)


def _geometry(info):
    if not isinstance(info, PageInfo):
        raise LayoutError("INVALID_GEOMETRY")
    for box in (info.media_box, info.crop_box):
        if (
            not isinstance(box, tuple)
            or len(box) != 4
            or any(type(v) not in (int, float) or not math.isfinite(v) for v in box)
            or box[2] <= box[0]
            or box[3] <= box[1]
        ):
            raise LayoutError("INVALID_GEOMETRY")
    if (
        type(info.rotation) is not int
        or info.rotation not in (0, 90, 180, 270)
        or type(info.user_unit) not in (int, float)
        or not math.isfinite(info.user_unit)
        or not 0 < info.user_unit <= 75000
    ):
        raise LayoutError("INVALID_GEOMETRY")
    media, crop = info.media_box, info.crop_box
    if crop[0] < media[0] or crop[1] < media[1] or crop[2] > media[2] or crop[3] > media[3]:
        raise LayoutError("INVALID_GEOMETRY")
    actual = _dimensions(crop, info.user_unit, info.rotation)
    if any(type(v) not in (int, float) or not math.isfinite(v) for v in (info.width_points, info.height_points)):
        raise LayoutError("INVALID_GEOMETRY")
    if any(not 0 < v <= 14400 for v in _dimensions(media, info.user_unit, info.rotation)):
        raise LayoutError("LIMIT_EXCEEDED")
    if any(abs(a - b) > EPSILON for a, b in zip(actual, (info.width_points, info.height_points), strict=True)):
        raise LayoutError("INVALID_GEOMETRY")


def _pairable(page):
    info = page.geometry
    return info.media_box == info.crop_box and all(
        abs(value - expected) <= EPSILON
        for value, expected in zip((info.width_points, info.height_points), A4, strict=True)
    )


def _matrix(info, offset):
    x0, y0, x1, y1 = info.media_box
    unit = info.user_unit
    # PDF /Rotate is clockwise in the displayed page. Normalize without scaling
    # physical size; UserUnit is a coordinate-to-point conversion, not fitting.
    return {
        0: (unit, 0, 0, unit, offset - x0 * unit, -y0 * unit),
        90: (0, -unit, unit, 0, offset - y0 * unit, x1 * unit),
        180: (-unit, 0, 0, -unit, offset + x1 * unit, y1 * unit),
        270: (0, unit, -unit, 0, offset + y1 * unit, -x0 * unit),
    }[info.rotation]


def _placement(piece, page, side, matrix):
    return Placement(piece.identity, piece.kind, page.document, page.index, side, matrix, page.geometry)


def _single(piece, page):
    info = page.geometry
    dimensions = _dimensions(info.media_box, info.user_unit, info.rotation)
    warnings = []
    if info.media_box != info.crop_box:
        warnings.append("ORIGINAL_CROP_PRESERVED")
    if info.paper == "CUSTOM":
        warnings.append("CUSTOM_MEDIA_REQUIRES_PRINTER_ACCEPTANCE")
    if info.width_points > info.height_points:
        warnings.append("LANDSCAPE_PRESERVED")
    if info.paper == "A4" and info.width_points < info.height_points and not _pairable(page):
        warnings.append("NONSTANDARD_A4_PRESERVED_UNPAIRED")
    return Sheet(
        info.media_box,
        info.crop_box,
        info.rotation,
        info.user_unit,
        *dimensions,
        (_placement(piece, page, "WHOLE", (1, 0, 0, 1, 0, 0)),),
        tuple(warnings),
    )


def plan(pieces, *, mode="FULL", maximum_pages=1000):
    """Preserve every page once, pairing exact physical A4 only within one piece."""
    if mode not in MODES or type(maximum_pages) is not int or not 1 <= maximum_pages <= 1000:
        raise LayoutError("INVALID_LAYOUT_OPTIONS")
    if not isinstance(pieces, tuple) or not 1 <= len(pieces) <= 1000:
        raise LayoutError("INVALID_PIECES")
    seen, count, sheets = set(), 0, []
    for piece in pieces:
        if (
            not isinstance(piece, LogicalPiece)
            or not isinstance(piece.identity, str)
            or not 1 <= len(piece.identity) <= 160
            or piece.identity in seen
            or piece.kind not in KINDS
            or not isinstance(piece.pages, tuple)
            or (piece.kind == "RESERVE") != (len(piece.pages) == 0)
        ):
            raise LayoutError("INVALID_PIECE_BOUNDARY")
        if mode == "CONTENTS" and piece.kind not in {"CONTENTS", "RESERVE"}:
            raise LayoutError("INVALID_CONTENTS_SCOPE")
        seen.add(piece.identity)
        pending = None
        for page in piece.pages:
            count += 1
            if count > maximum_pages:
                raise LayoutError("LIMIT_EXCEEDED")
            if (
                not isinstance(page, LogicalPage)
                or not isinstance(page.document, str)
                or not 1 <= len(page.document) <= 160
                or type(page.index) is not int
                or page.index < 0
            ):
                raise LayoutError("INVALID_PAGE_IDENTITY")
            _geometry(page.geometry)
            pairable = piece.kind == "MUSIC" and _pairable(page)
            if pending is not None:
                if pairable and page.document == pending.document and page.index == pending.index + 1:
                    media = (0, 0, *A3)
                    sheets.append(
                        Sheet(
                            media,
                            media,
                            0,
                            1,
                            *A3,
                            (
                                _placement(piece, pending, "LEFT", _matrix(pending.geometry, 0)),
                                _placement(piece, page, "RIGHT", _matrix(page.geometry, A4[0])),
                            ),
                        )
                    )
                    pending = None
                    continue
                sheets.append(_single(piece, pending))
                pending = None
            if pairable:
                pending = page
            else:
                sheets.append(_single(piece, page))
        if pending is not None:
            sheets.append(_single(piece, pending))
    if not count:
        raise LayoutError("EMPTY_OUTPUT")
    return PrintPlan(mode, pieces, tuple(sheets))
