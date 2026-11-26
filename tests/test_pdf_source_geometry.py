"""Opt-in source geometry does not alter legacy PDF inspection contracts."""

from dataclasses import asdict, replace
from io import BytesIO

import pytest
from pypdf import PdfReader

from core.page_geometry import GeometryError, PageGeometry
from core.pdf import Limits, Processor
from core.pdf.structure import inspect, page_info, source_page_geometry
from tests.pdf_fixtures import pdf


@pytest.mark.parametrize("rotation", [0, 90, 180, 270, -90, 450])
@pytest.mark.parametrize("unit", [0.5, 1, 2])
def test_lossless_original_crop_and_legacy_effective_geometry_parity(rotation, unit):
    reader = PdfReader(BytesIO(pdf(sizes=((100, 100),), crop=(-10, 20, 120, 80), rotation=rotation, unit=unit)))
    page = reader.pages[0]
    legacy = page_info(page)
    source = source_page_geometry(page)
    assert source.page_info == legacy
    assert source.original_crop_box == (-10, 20, 120, 80)
    assert legacy.crop_box == (0, 20, 100, 80)
    assert set(asdict(legacy)) == {"media_box", "crop_box", "user_unit", "rotation", "width_points", "height_points"}
    assert inspect(reader, [legacy], Limits(), False) == {"pages": [asdict(legacy)]}
    geometry = PageGeometry.from_source_page(source)
    assert geometry.crop_box == source.original_crop_box
    assert geometry.effective_box == legacy.crop_box
    assert geometry.display_points == (legacy.width_points, legacy.height_points)
    assert geometry.rotation == rotation % 360


def test_equal_effective_boxes_different_original_boxes_change_fingerprint():
    pages = [
        PdfReader(BytesIO(pdf(sizes=((100, 100),), crop=crop))).pages[0]
        for crop in [(-10, 0, 110, 100), (-20, 0, 120, 100)]
    ]
    sources = [source_page_geometry(page) for page in pages]
    assert sources[0].page_info == sources[1].page_info
    geometries = [PageGeometry.from_source_page(source) for source in sources]
    assert geometries[0].effective_box == geometries[1].effective_box
    assert geometries[0].fingerprint != geometries[1].fingerprint


def test_legacy_metadata_cannot_invent_original_crop():
    legacy = page_info(PdfReader(BytesIO(pdf())).pages[0])
    with pytest.raises(GeometryError, match="ORIGINAL_CROPBOX_REQUIRED"):
        PageGeometry.from_source_page(legacy)


def test_bridge_rejects_inconsistent_retained_source_evidence():
    source = source_page_geometry(PdfReader(BytesIO(pdf(sizes=((100, 100),)))).pages[0])
    inconsistent = replace(source, original_crop_box=(10, 10, 90, 90))
    with pytest.raises(GeometryError, match="INCONSISTENT_SOURCE_GEOMETRY"):
        PageGeometry.from_source_page(inconsistent)


def test_legacy_parser_limits_not_replaced_by_geometry_bridge_limits():
    # Existing parser bounds effective dimensions; the region contract also
    # bounds MediaBox. Opt-in geometry rejection must not affect legacy parsing.
    page = PdfReader(BytesIO(pdf(sizes=((15000, 100),), crop=(0, 0, 100, 100)))).pages[0]
    source = source_page_geometry(page)
    assert source.page_info.width_points == 100
    with pytest.raises(GeometryError, match="GEOMETRY_LIMIT"):
        PageGeometry.from_source_page(source)


def test_existing_isolated_inspection_ipc_unchanged(tmp_path):
    data = pdf(sizes=((100, 100),), crop=(-10, 20, 120, 80), rotation=90, unit=2)
    legacy = page_info(PdfReader(BytesIO(data)).pages[0])
    result = Processor(tmp_path).inspect(data)
    assert result.pages == (legacy,)
    assert "original_crop_box" not in asdict(result.pages[0])
