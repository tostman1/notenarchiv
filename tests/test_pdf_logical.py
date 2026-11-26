"""Explicit reviewed-region primitives preserve vectors, order and source bytes."""

import hashlib
from io import BytesIO

import pytest
from pypdf import PdfReader

from core.pdf import PdfError, Processor
from tests.pdf_fixtures import A3, pdf


def test_native_a3_is_not_automatically_split(tmp_path):
    processor = Processor(tmp_path)
    source = pdf(sizes=(A3,))
    digest = hashlib.sha256(source).hexdigest()
    result = processor.logical_pages([source], [{"input": 0, "page": 0, "bounds": (0, 0, *A3), "orientation": 0}])
    info = processor.inspect(result)
    assert len(info.pages) == 1
    assert (info.pages[0].width_points, info.pages[0].height_points) == A3
    assert hashlib.sha256(source).hexdigest() == digest
    assert "Synthetic" in processor.extract_text(result)[0]


def test_repeated_regions_and_sources_keep_explicit_order(tmp_path):
    processor = Processor(tmp_path)
    inputs = [pdf(sizes=((300, 200),), rotation=90, unit=2), pdf(sizes=((100, 200),))]
    selections = [
        {"input": 1, "page": 0, "bounds": (0, 0, 100, 200), "orientation": 0},
        {"input": 0, "page": 0, "bounds": (0, 0, 300, 400), "orientation": 90},
        {"input": 0, "page": 0, "bounds": (300, 0, 600, 400), "orientation": 0},
        {"input": 0, "page": 0, "bounds": (0, 0, 300, 400), "orientation": 90},
    ]
    result = processor.logical_pages(inputs, selections)
    pages = processor.inspect(result).pages
    assert [(page.width_points, page.height_points) for page in pages] == [
        (100, 200),
        (300, 400),
        (400, 300),
        (300, 400),
    ]
    reader = PdfReader(BytesIO(result))
    assert all(not page.get("/Annots") for page in reader.pages)
    assert b" re" in reader.pages[1].get_contents().get_data()


def test_invalid_bounds_fail_closed_in_isolated_parser(tmp_path):
    processor = Processor(tmp_path)
    source = pdf(sizes=((100, 200),))
    with pytest.raises(PdfError, match="INVALID_PAGE"):
        processor.logical_pages([source], [{"input": 0, "page": 0, "bounds": (0, 0, 101, 200), "orientation": 0}])
    for bounds in ((0, 0, float("nan"), 1), (1, 0, 0, 1)):
        with pytest.raises(ValueError):
            processor.logical_pages([source], [{"input": 0, "page": 0, "bounds": bounds, "orientation": 0}])
    assert not list(tmp_path.iterdir())


def test_crop_offset_and_visible_annotations_are_not_silently_discarded(tmp_path):
    processor = Processor(tmp_path)
    source = pdf(sizes=((300, 200),), crop=(20, 30, 220, 180), unit=2)
    result = processor.logical_pages(
        [source], [{"input": 0, "page": 0, "bounds": (40, 60, 440, 360), "orientation": 0}]
    )
    info = processor.inspect(result).pages[0]
    assert info.media_box == (0, 0, 400, 300)
    assert info.user_unit == 1
    unsafe = pdf(annotation="/Text")
    with pytest.raises(PdfError, match="UNSUPPORTED_ANNOTATION"):
        processor.logical_pages([unsafe], [{"input": 0, "page": 0, "bounds": (0, 0, 100, 100), "orientation": 0}])
