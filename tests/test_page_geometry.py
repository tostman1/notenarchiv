"""Synthetic canonical geometry and invertible display transforms; no PDFs/I/O."""

import math
from dataclasses import FrozenInstanceError

import pytest

from core.page_geometry import SCHEMA, DisplayTransform, GeometryError, PageGeometry, RectangleRegion


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
@pytest.mark.parametrize("unit", [0.5, 1, 2.5])
@pytest.mark.parametrize("scale", [0.125, 1, 3.25])
def test_offset_crop_user_unit_and_scale_roundtrip(rotation, unit, scale):
    page = PageGeometry((-20, -10, 300, 200), (10, 20, 210, 120), rotation, unit)
    transform = DisplayTransform(page, scale)
    for x, y in [(10, 20), (210, 120), (10, 120), (210, 20), (73.125, 61.25)]:
        point = x * unit, y * unit
        pixels = transform.to_pixels(point)
        assert transform.to_points(pixels) == pytest.approx(point, abs=1e-7)
        assert transform.to_pixels(transform.to_points(pixels)) == pytest.approx(pixels, abs=1e-7)


@pytest.mark.parametrize("rotation,expected", [(0, (0, 100)), (90, (0, 0)), (180, (200, 0)), (270, (100, 200))])
def test_clockwise_rotation_and_top_left_pixel_origin(rotation, expected):
    page = PageGeometry((0, 0, 300, 200), (10, 20, 210, 120), rotation)
    assert DisplayTransform(page, 1).to_pixels((10, 20)) == expected


def test_effective_crop_intersection_retains_original_box_and_physical_region():
    page = PageGeometry((0, 0, 100, 100), (-10, 20, 120, 80), user_unit=2)
    assert page.crop_box == (-10, 20, 120, 80)
    assert page.effective_box == (0, 20, 100, 80)
    assert page.effective_points == (0, 40, 200, 160)
    assert page.region(page.effective_points).bounds == (0, 40, 200, 160)
    with pytest.raises(GeometryError, match="REGION_OUTSIDE_PAGE"):
        page.region((-0.00000001, 40, 200, 160))


def test_geometry_is_immutable_normalized_and_deterministic():
    media, crop = [0, 0, 100, 100], [10, 10, 90, 90]
    page = PageGeometry(media, crop)
    equivalent = PageGeometry((-0.0, 0.0, 100.0, 100.0), (10.0, 10.0, 90.0, 90.0))
    media[2], crop[2] = 200, 200
    assert page == equivalent and page.fingerprint == equivalent.fingerprint
    assert page.canonical()["schema"] == SCHEMA and len(page.fingerprint) == 64
    result = page.canonical()
    result["rotation"] = 90
    assert page.rotation == 0
    with pytest.raises(FrozenInstanceError):
        page.rotation = 90
    region = RectangleRegion(page, [10, 10, 20, 20])
    assert isinstance(region.bounds, tuple)
    with pytest.raises(FrozenInstanceError):
        region.bounds = (0, 0, 1, 1)


@pytest.mark.parametrize(
    "change",
    [
        {"media_box": (0, 0, 110, 100)},
        {"crop_box": (10, 10, 80, 90)},
        {"crop_box": (-10, 0, 100, 100)},
        {"rotation": 90},
        {"user_unit": 2},
    ],
)
def test_source_geometry_changes_fingerprint(change):
    values = dict(media_box=(0, 0, 100, 100), crop_box=(0, 0, 100, 100))
    before = PageGeometry(**values)
    values.update(change)
    assert before.fingerprint != PageGeometry(**values).fingerprint


@pytest.mark.parametrize(
    "box",
    [(0, 0, 0, 1), (2, 0, 1, 1), (0, 0, 1), (0, 0, math.inf, 1), (0, math.nan, 1, 1), (False, 0, 1, 1), ("0", 0, 1, 1)],
)
def test_malformed_boxes_fail_closed(box):
    with pytest.raises(GeometryError):
        PageGeometry(box, (0, 0, 1, 1))


@pytest.mark.parametrize("unit", [0, -1, math.nan, math.inf, True, "1", 75001])
def test_invalid_user_unit(unit):
    with pytest.raises(GeometryError):
        PageGeometry((0, 0, 100, 100), (0, 0, 100, 100), user_unit=unit)


@pytest.mark.parametrize("rotation", [45, 360, -90, 90.0, True])
def test_noncanonical_rotation_rejected(rotation):
    with pytest.raises(GeometryError):
        PageGeometry((0, 0, 100, 100), (0, 0, 100, 100), rotation)


@pytest.mark.parametrize("bounds", [(0, 0, 0, 10), (-1, 0, 10, 10), (0, 0, 101, 10), (0, 0, 10, math.inf)])
def test_region_approval_never_clips_or_accepts_degenerate_bounds(bounds):
    with pytest.raises(GeometryError):
        PageGeometry((0, 0, 100, 100), (0, 0, 100, 100)).region(bounds)


@pytest.mark.parametrize("scale", [0, -1, math.nan, math.inf, True, "1", 1e308])
def test_invalid_display_scale(scale):
    with pytest.raises(GeometryError):
        DisplayTransform(PageGeometry((0, 0, 100, 100), (0, 0, 100, 100)), scale)


def test_outside_nonfinite_points_and_disjoint_crop_rejected():
    with pytest.raises(GeometryError):
        PageGeometry((0, 0, 100, 100), (110, 110, 120, 120))
    transform = DisplayTransform(PageGeometry((0, 0, 100, 100), (0, 0, 100, 100)), 2)
    for point in [(-1, 0), (101, 0), (math.nan, 0), (True, 0)]:
        with pytest.raises(GeometryError):
            transform.to_pixels(point)
    for point in [(-1, 0), (201, 0), (math.inf, 0)]:
        with pytest.raises(GeometryError):
            transform.to_points(point)


def test_existing_physical_page_limit_and_overflow_fail_closed():
    with pytest.raises(GeometryError):
        PageGeometry((0, 0, 14401, 100), (0, 0, 100, 100))
    with pytest.raises(GeometryError):
        PageGeometry((1e308, 0, 1.1e308, 100), (1e308, 0, 1.1e308, 100), user_unit=2)


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
@pytest.mark.parametrize("scale", [0.125, 1, 3.25])
def test_decimal_crop_exact_pixel_edges_preserve_exact_pdf_endpoints(rotation, scale):
    page = PageGeometry((-1, -1, 1, 1), (-0.3, -0.3, 0.1, 0.1), rotation)
    transform = DisplayTransform(page, scale)
    # Deterministic reproducer: -0.3 + (0.1 - -0.3) > 0.1 by an ulp.
    assert -0.3 + (0.1 - -0.3) > 0.1
    for x in (-0.3, 0.1):
        for y in (-0.3, 0.1):
            point = (x, y)
            assert transform.to_points(transform.to_pixels(point)) == point
    width, height = (value * scale for value in page.display_points)
    for pixel in ((0, 0), (width, 0), (0, height), (width, height)):
        assert transform.to_pixels(transform.to_points(pixel)) == pixel
    with pytest.raises(GeometryError, match="POINT_OUTSIDE_PAGE"):
        transform.to_points((math.nextafter(width, math.inf), height))
    with pytest.raises(GeometryError, match="REGION_OUTSIDE_PAGE"):
        page.region((-0.3, -0.3, math.nextafter(0.1, math.inf), 0.1))
