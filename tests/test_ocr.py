"""Synthetic OCR contracts; representative musical accuracy remains manual."""

import hashlib
from dataclasses import replace

import pytest

from core.ocr import Engine, OcrError, Profile, parse_tsv
from core.processes import ProcessCleanupError


def test_native_line_identity_keeps_side_by_side_headings_separate():
    from apps.archive.recognition import ocr_lines

    output = (
        b"level\tpage_num\tblock_num\tpar_num\tline_num\tleft\ttop\twidth\theight\tconf\ttext\n"
        b"5\t1\t1\t1\t1\t10\t20\t40\t15\t90\tFirst\n"
        b"5\t1\t1\t1\t1\t55\t21\t40\t15\t90\tMarch\n"
        b"5\t1\t2\t1\t1\t200\t20\t40\t15\t90\tSecond\n"
        b"5\t1\t2\t1\t1\t245\t20\t40\t15\t90\tPolka\n"
    )
    words = parse_tsv(output)
    assert words[0]["line"] == [1, 1, 1, 1]
    assert ocr_lines(words) == ["First March", "Second Polka"]
    with pytest.raises(OcrError, match="INVALID_OUTPUT"):
        parse_tsv(output.replace(b"5\t1\t2", b"5\t1\t-2"))


TSV = b"level\tleft\ttop\twidth\theight\tconf\ttext\n5\t10\t20\t30\t15\t87\tPosaune II\n"


def test_tsv_preserves_bounded_words_boxes_and_uncertainty():
    assert parse_tsv(TSV) == [{"text": "Posaune II", "box": [10, 20, 40, 35], "confidence": 0.87}]
    for output in (
        b"broken",
        TSV.replace(b"87", b"nan"),
        TSV.replace(b"30", b"-1"),
        TSV.replace(b"87", b"101"),
        TSV.splitlines(keepends=True)[0] + b"5\t10\n",
    ):
        with pytest.raises(OcrError, match="INVALID_OUTPUT"):
            parse_tsv(output)
    with pytest.raises(OcrError, match="OUTPUT_LIMIT"):
        parse_tsv(TSV + TSV.splitlines(keepends=True)[1], maximum=1)


@pytest.fixture
def engine(tmp_path):
    tmp_path.chmod(0o700)
    executable = tmp_path / "tesseract"
    executable.write_bytes(b"synthetic executable")
    for language in ("deu", "eng"):
        (tmp_path / f"{language}.traineddata").write_bytes(language.encode())
    return Engine(tmp_path, executable, tmp_path)


def test_cache_includes_geometry_revision_profile_runtime_and_rules(engine):
    args = dict(sha256=hashlib.sha256(b"pdf").hexdigest(), page=0, bounds=None, orientation=0, revision=1, rules="v1")
    key = engine.cache_key(**args)
    for field, value in (
        ("page", 1),
        ("bounds", [0, 0, 100, 100]),
        ("orientation", 90),
        ("revision", 2),
        ("rules", "v2"),
    ):
        assert engine.cache_key(**{**args, field: value}) != key
    engine.profile = replace(engine.profile, dpi=300)
    assert engine.cache_key(**args) != key
    engine.profile = Profile()
    engine.runtime_key = "changed"
    assert engine.cache_key(**args) != key


def test_partial_text_never_skips_ocr_and_uncertain_cleanup_retains_stage(engine, monkeypatch):
    calls = []
    monkeypatch.setattr(engine.processor, "logical_pages", lambda *a: b"logical")
    monkeypatch.setattr(engine.processor, "extract_text", lambda *a: ("Misleading title",))
    monkeypatch.setattr(engine.processor, "render", lambda *a, **k: b"synthetic PNG")

    def run(arguments, **kwargs):
        calls.append(kwargs)
        from pathlib import Path

        Path(arguments[2] + ".tsv").write_bytes(TSV)

    monkeypatch.setattr("core.ocr.run_process", run)
    result = engine.recognize_page(b"pdf", page=0, bounds=[0, 0, 100, 100], rules="v1")
    assert result["text_layer"] == "Misleading title"
    assert result["words"][0]["text"] == "Posaune II"
    assert calls[0]["env"] == {"OMP_THREAD_LIMIT": "2"}
    assert calls[0]["memory_bytes"] == 402_653_184
    assert not list(engine.processor.root.glob("pdf-*"))

    def uncertain(*a, **k):
        raise ProcessCleanupError

    monkeypatch.setattr("core.ocr.run_process", uncertain)
    with pytest.raises(ProcessCleanupError):
        engine.recognize_page(b"pdf", page=0, bounds=[0, 0, 100, 100], rules="v1")
    assert len(list(engine.processor.root.glob("pdf-*"))) == 1


def test_profile_rejects_unbounded_or_shell_like_configuration():
    for kwargs in ({"dpi": 301}, {"timeout": True}, {"languages": "eng;curl"}, {"max_words": 10000}):
        with pytest.raises(ValueError):
            Profile(**kwargs)


def test_native_package_manifest_changes_runtime_identity(engine, tmp_path):
    manifest = tmp_path / "installed"
    manifest.write_bytes(b"synthetic libtesseract version 1")
    first = Engine(tmp_path, engine.executable, engine.tessdata, runtime_manifest=manifest)
    manifest.write_bytes(b"synthetic libtesseract version 2")
    second = Engine(tmp_path, engine.executable, engine.tessdata, runtime_manifest=manifest)
    assert first.runtime_key != second.runtime_key


def test_real_pdf_geometry_text_and_rendering_with_local_ocr_stub(engine, monkeypatch):
    import io
    from pathlib import Path

    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import RectangleObject
    from reportlab.pdfgen.canvas import Canvas

    stream = io.BytesIO()
    canvas = Canvas(stream, pagesize=(180, 240))
    canvas.drawString(30, 120, "Synthetic musical title")
    canvas.save()
    writer = PdfWriter()
    page = PdfReader(stream).pages[0]
    page.cropbox = RectangleObject((10, 20, 170, 220))
    page.rotate(90)
    writer.add_page(page)
    output = io.BytesIO()
    writer.write(output)

    def run(arguments, **kwargs):
        assert Path(arguments[1]).read_bytes().startswith(b"\x89PNG")
        Path(arguments[2] + ".tsv").write_bytes(TSV)

    monkeypatch.setattr("core.ocr.run_process", run)
    result = engine.recognize_page(output.getvalue(), page=0, rules="v1")
    assert result["bounds"] == [10, 20, 170, 220]
    assert "Synthetic musical title" in result["text_layer"]
    assert result["words"] == parse_tsv(TSV)
