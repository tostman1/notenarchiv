"""Pure deterministic SMB naming, without production archive paths."""

import pytest

from core.naming import component, pdf_name, with_suffix
from core.paths import storage_key


@pytest.mark.parametrize("value", ["CON", "con.pdf", "LPT1", "COM¹", "PRN", "NUL", "AUX"])
def test_reserved_device_names_are_disarmed(value):
    assert component(value).startswith("_")


def test_names_are_unicode_normalized_bounded_and_smb_safe():
    assert component("  Ma\u0308rsch:*?  B /C. ") == "Märsch___ B _C"
    assert component(".. ") == "Unbekannt"
    assert component("\x00abc\n") == "_abc_"
    assert len(component("音" * 200).encode("utf-8")) <= 100
    assert not component(".staging").startswith(".")
    assert pdf_name("Synthetic/Scanner.PDF") == "Scanner.pdf"
    assert storage_key("MÄRSCH.pdf") == storage_key("Ma\u0308rsch.PDF")


def test_collision_suffix_is_stable_specific_and_only_added_when_requested():
    identifier = "ab" * 16
    assert with_suffix("Title/Part.pdf", identifier) == "Title/Part--abababababab.pdf"
    assert with_suffix("Title/Part.pdf", identifier, 1) == "Title/Part--abababababab-1.pdf"
    with pytest.raises(ValueError):
        with_suffix("Title/Part.pdf", "not-an-id")


def test_unsupported_filesystem_platform_fails_before_any_open(tmp_path, monkeypatch):
    from core import files

    monkeypatch.setattr(files.os, "supports_dir_fd", set())
    calls = []
    monkeypatch.setattr(files.os, "open", lambda *args, **kwargs: calls.append(args))
    with pytest.raises(files.FileError, match="UNSUPPORTED_FILESYSTEM_API"), files.Root(tmp_path, writable=True):
        pytest.fail("Unsupported API must fail closed")
    assert calls == []
