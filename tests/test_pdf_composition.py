"""Reading composition preserves music graphics, shared contents and Unicode."""

from io import BytesIO

import pytest
from pypdf import PdfReader

from core.pdf import PdfError, Processor
from tests.pdf_fixtures import A3, A4, pdf


def piece(number, state="MUSIC", *, title="Synthetic Übung Straße", data=None):
    return {
        "number": number,
        "title": title,
        "state": state,
        "data": pdf() if state == "MUSIC" and data is None else data,
    }


def test_contents_only_rejects_musical_bytes_and_preserves_reserve_labels(tmp_path):
    processor = Processor(tmp_path)
    with pytest.raises(ValueError, match="music inputs"):
        processor.compose([piece(1)], project="Synthetic", music=False)
    with pytest.raises(ValueError, match="Contents entries"):
        processor.compose([piece(1, "CONTENTS")], project="Synthetic")
    result = processor.compose(
        [piece(1, "CONTENTS"), piece(2, "RESERVE")], project="Synthetisches Projekt", music=False
    )
    reader = PdfReader(BytesIO(result))
    text = reader.pages[0].extract_text()
    assert len(reader.pages) == 1 and "Synthetisches Projekt" in text and "2. Synthetic Übung Straße — Reserve" in text
    assert "Noten fehlen" not in text


def test_contents_reserve_placeholder_unicode_no_music_overlay(tmp_path):
    processor = Processor(tmp_path)
    music = pdf(sizes=(A3, A4, (841.8898, 595.2756)))
    result = processor.compose([piece(1, data=music), piece(2, "RESERVE"), piece(3, "MISSING")], project="Frühling")
    reader = PdfReader(BytesIO(result))
    assert len(reader.pages) == 5
    assert "Inhaltsverzeichnis" in reader.pages[0].extract_text()
    assert "2. Synthetic Übung Straße — Reserve" in reader.pages[0].extract_text()
    assert "Noten fehlen" in reader.pages[-1].extract_text()
    source = PdfReader(BytesIO(music))
    for original, copied in zip(source.pages, reader.pages[1:4], strict=True):
        assert original.mediabox == copied.mediabox and original.cropbox == copied.cropbox
        assert original.get_contents().get_data() == copied.get_contents().get_data()


@pytest.mark.parametrize("rotation,unit,crop", [(90, 1, None), (180, 1, (30, 30, 500, 800)), (0, 2, None)])
def test_original_rotation_crop_userunit_and_vectors_preserved(tmp_path, rotation, unit, crop):
    data = pdf(rotation=rotation, unit=unit, crop=crop)
    output = Processor(tmp_path).compose([piece(8, data=data)], project="Synthetic", contents=False)
    source, result = PdfReader(BytesIO(data)).pages[0], PdfReader(BytesIO(output)).pages[0]
    assert source.mediabox == result.mediabox and source.cropbox == result.cropbox
    assert source.rotation == result.rotation and source.user_unit == result.user_unit
    assert source.get_contents().get_data() == result.get_contents().get_data()


def test_cover_optional_and_contents_pagination(tmp_path):
    processor = Processor(tmp_path)
    pieces = [piece(n, "RESERVE", title=f"Synthetic Stück {n}") for n in range(1, 101)]
    plain = PdfReader(BytesIO(processor.compose(pieces, project="Synthetic")))
    covered = PdfReader(
        BytesIO(
            processor.compose(pieces, project="Synthetic", participant="Jürgen", assignment="Posaune 2", cover=True)
        )
    )
    assert len(plain.pages) >= 3 and len(covered.pages) == len(plain.pages) + 1
    assert "Jürgen" in covered.pages[0].extract_text()
    assert "100. Synthetic Stück 100" in plain.pages[-1].extract_text()
    assert "Inhaltsverzeichnis" in plain.pages[0].extract_text()


def test_separate_piece_pages_never_paired_and_excerpt_has_no_contents(tmp_path):
    output = Processor(tmp_path).compose([piece(4), piece(9)], project="Synthetic", contents=False)
    reader = PdfReader(BytesIO(output))
    assert len(reader.pages) == 2 and all(float(p.mediabox.width) < 600 for p in reader.pages)
    assert all("Inhaltsverzeichnis" not in p.extract_text() for p in reader.pages)


def test_unsupported_unicode_is_error_not_missing_glyph(tmp_path):
    with pytest.raises(PdfError, match="UNSUPPORTED_TEXT"):
        Processor(tmp_path).compose([piece(1, "MISSING", title="Synthetic 🎵")], project="Synthetic")


def test_invalid_position_order_and_unacknowledged_state_rejected(tmp_path):
    with pytest.raises(ValueError):
        Processor(tmp_path).compose([piece(2), piece(1)], project="Synthetic")
    with pytest.raises(ValueError):
        Processor(tmp_path).compose([piece(1, "PENDING")], project="Synthetic")


def test_generated_text_does_not_interpret_markup(tmp_path):
    output = Processor(tmp_path).compose([piece(1, "MISSING", title="<script> & Synthetic")], project="Synthetic")
    assert "<script> & Synthetic" in PdfReader(BytesIO(output)).pages[0].extract_text()


def test_generated_marchbook_dimensions_and_page_limit(tmp_path):
    from core.pdf import Limits

    data = Processor(tmp_path).compose([piece(1, "MISSING")], project="Synthetic", page_size=(481.89, 340.16))
    assert float(PdfReader(BytesIO(data)).pages[0].mediabox.width) == pytest.approx(481.89)
    with pytest.raises(PdfError, match="LIMIT_EXCEEDED"):
        Processor(tmp_path, limits=Limits(max_pages=1)).compose([piece(1)], project="Synthetic")


def test_oversized_heading_fails_without_clipping(tmp_path):
    with pytest.raises(PdfError, match="LIMIT_EXCEEDED"):
        Processor(tmp_path).compose([piece(1, "MISSING")], project="Synthetic " * 90, cover=True, page_size=(140, 140))


def test_composition_retains_annotation_fail_closed_boundary(tmp_path):
    with pytest.raises(PdfError, match="UNSUPPORTED_ANNOTATION"):
        Processor(tmp_path).compose([piece(1, data=pdf(annotation="/Widget"))], project="Synthetic")


def test_composition_is_deterministic_for_same_inputs(tmp_path):
    processor = Processor(tmp_path)
    positions = [piece(1), piece(2, "RESERVE"), piece(3, "MISSING")]
    assert processor.compose(positions, project="Synthetic") == processor.compose(positions, project="Synthetic")
