"""Versioned immutable PDF-point region geometry; no parser or rendering imports.

Input PDF boxes are default-user-space coordinates, as in core.pdf.types.PageInfo.
Canonical regions use physical points (input coordinates multiplied by UserUnit),
with the PDF bottom-left axis convention. UI pixels use top-left origin after
clockwise /Rotate. Original CropBox is retained separately from its intersection.
"""

import hashlib
import json
import math
from dataclasses import dataclass

SCHEMA = "pdf-point-rectangle-v1"
ROUNDTRIP_TOLERANCE = 1e-7  # Physical PDF points, never a containment allowance.


class GeometryError(ValueError):
    pass


def _number(value):
    if type(value) not in (int, float):
        raise GeometryError("INVALID_GEOMETRY")
    try:
        result = float(value)
    except (OverflowError, ValueError):
        raise GeometryError("INVALID_GEOMETRY") from None
    if not math.isfinite(result):
        raise GeometryError("INVALID_GEOMETRY")
    return 0.0 if result == 0 else result


def _box(value):
    if type(value) not in (tuple, list) or len(value) != 4:
        raise GeometryError("INVALID_GEOMETRY")
    result = tuple(_number(item) for item in value)
    if result[2] <= result[0] or result[3] <= result[1]:
        raise GeometryError("INVALID_GEOMETRY")
    return result


def _point(value):
    if type(value) not in (tuple, list) or len(value) != 2:
        raise GeometryError("INVALID_GEOMETRY")
    return tuple(_number(item) for item in value)


def _contained(box, bounds):
    return bounds[0] <= box[0] < box[2] <= bounds[2] and bounds[1] <= box[1] < box[3] <= bounds[3]


@dataclass(frozen=True)
class PageGeometry:
    media_box: tuple[float, float, float, float]
    crop_box: tuple[float, float, float, float]
    rotation: int = 0
    user_unit: float = 1.0

    def __post_init__(self):
        media, crop = _box(self.media_box), _box(self.crop_box)
        unit = _number(self.user_unit)
        if not 0 < unit <= 75000 or type(self.rotation) is not int or self.rotation not in (0, 90, 180, 270):
            raise GeometryError("INVALID_GEOMETRY")
        object.__setattr__(self, "media_box", media)
        object.__setattr__(self, "crop_box", crop)
        object.__setattr__(self, "user_unit", unit)
        _box(self.effective_box)
        physical = self.media_points
        if any(not 0 < value <= 14400 for value in (physical[2] - physical[0], physical[3] - physical[1])):
            raise GeometryError("GEOMETRY_LIMIT")

    @property
    def effective_box(self):
        m, b = self.media_box, self.crop_box
        return max(m[0], b[0]), max(m[1], b[1]), min(m[2], b[2]), min(m[3], b[3])

    @property
    def media_points(self):
        return tuple(_number(value * self.user_unit) for value in self.media_box)

    @property
    def effective_points(self):
        return _box(tuple(_number(value * self.user_unit) for value in self.effective_box))

    @property
    def display_points(self):
        x0, y0, x1, y1 = self.effective_points
        size = x1 - x0, y1 - y0
        return size[::-1] if self.rotation in (90, 270) else size

    def canonical(self):
        return {
            "schema": SCHEMA,
            "media_box": self.media_box,
            "crop_box": self.crop_box,
            "effective_box": self.effective_box,
            "rotation": self.rotation,
            "user_unit": self.user_unit,
        }

    @property
    def fingerprint(self):
        encoded = json.dumps(self.canonical(), sort_keys=True, separators=(",", ":"), allow_nan=False)
        return hashlib.sha256(encoded.encode("ascii")).hexdigest()

    def region(self, bounds):
        return RectangleRegion(self, bounds)


@dataclass(frozen=True)
class RectangleRegion:
    page: PageGeometry
    bounds: tuple[float, float, float, float]

    def __post_init__(self):
        if not isinstance(self.page, PageGeometry):
            raise GeometryError("INVALID_GEOMETRY")
        bounds = _box(self.bounds)
        if not _contained(bounds, self.page.effective_points):
            raise GeometryError("REGION_OUTSIDE_PAGE")
        object.__setattr__(self, "bounds", bounds)

    def canonical(self):
        return {"schema": SCHEMA, "page_fingerprint": self.page.fingerprint, "bounds_points": self.bounds}


@dataclass(frozen=True)
class DisplayTransform:
    page: PageGeometry
    pixels_per_point: float

    def __post_init__(self):
        if not isinstance(self.page, PageGeometry):
            raise GeometryError("INVALID_GEOMETRY")
        scale = _number(self.pixels_per_point)
        if scale <= 0 or any(
            not math.isfinite(value * scale) or value * scale <= 0 for value in self.page.display_points
        ):
            raise GeometryError("INVALID_SCALE")
        object.__setattr__(self, "pixels_per_point", scale)

    def _forward(self, point):
        x0, y0, x1, y1 = self.page.effective_points
        x, y = point
        return {0: (x - x0, y1 - y), 90: (y - y0, x - x0), 180: (x1 - x, y - y0), 270: (y1 - y, x1 - x)}[
            self.page.rotation
        ]

    def _inverse(self, point):
        x0, y0, x1, y1 = self.page.effective_points
        u, v = point
        return {0: (x0 + u, y1 - v), 90: (x0 + v, y0 + u), 180: (x1 - u, y0 + v), 270: (x1 - v, y1 - u)}[
            self.page.rotation
        ]

    def to_pixels(self, point):
        point = _point(point)
        x0, y0, x1, y1 = self.page.effective_points
        if not x0 <= point[0] <= x1 or not y0 <= point[1] <= y1:
            raise GeometryError("POINT_OUTSIDE_PAGE")
        pixels = tuple(_number(value * self.pixels_per_point) for value in self._forward(point))
        restored = self._inverse(tuple(value / self.pixels_per_point for value in pixels))
        if any(abs(a - b) > ROUNDTRIP_TOLERANCE for a, b in zip(point, restored, strict=True)):
            raise GeometryError("TRANSFORM_PRECISION")
        return pixels

    def to_points(self, pixels):
        pixels = _point(pixels)
        width, height = (value * self.pixels_per_point for value in self.page.display_points)
        if not 0 <= pixels[0] <= width or not 0 <= pixels[1] <= height:
            raise GeometryError("POINT_OUTSIDE_PAGE")
        result = tuple(
            _number(value) for value in self._inverse(tuple(value / self.pixels_per_point for value in pixels))
        )
        # Exact UI boundaries select exact PDF boundaries, not a subtraction /
        # addition round trip that can overshoot by an ulp. Interior points are
        # never clipped and containment tolerances remain unchanged.
        x0, y0, x1, y1 = self.page.effective_points
        edges = {
            0: ((0, x0, x1), (1, y1, y0)),
            90: ((1, x0, x1), (0, y0, y1)),
            180: ((0, x1, x0), (1, y0, y1)),
            270: ((1, x1, x0), (0, y1, y0)),
        }[self.page.rotation]
        result = tuple(
            low if pixels[axis] == 0 else high if pixels[axis] == (width, height)[axis] else value
            for value, (axis, low, high) in zip(result, edges, strict=True)
        )
        restored = self.to_pixels(result)
        if any(abs(a - b) / self.pixels_per_point > ROUNDTRIP_TOLERANCE for a, b in zip(pixels, restored, strict=True)):
            raise GeometryError("TRANSFORM_PRECISION")
        return result
