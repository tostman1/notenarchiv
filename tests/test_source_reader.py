"""Actual shared source traversal and native Windows handle safety."""

import hashlib
import os
import stat
import subprocess

import pytest

from core import files, inventory

windows = pytest.mark.skipif(os.name != "nt", reason="Native Windows source handles")


def junction(path, target):
    result = subprocess.run(
        ["cmd.exe", "/d", "/c", "mklink", "/J", str(path), str(target)],
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, "Synthetic junction creation failed"


def test_source_inventory_and_hash_use_consistent_backend_metadata(tmp_path):
    (tmp_path / "nested").mkdir()
    path = tmp_path / "nested" / "Score.pdf"
    path.write_bytes(b"synthetic source")
    with files.source_root(tmp_path) as root:
        assert root.writable is False
        rows = inventory.scan(root, "")
        entry = next(row for row in rows if row["path"] == "nested/Score.pdf")
        digest, data, info = inventory.read_hash(root, entry["path"], maximum=1024, expected=entry["fingerprint"])
        assert digest == hashlib.sha256(b"synthetic source").hexdigest() and data == b"synthetic source"
        assert files.fingerprint(root.metadata(entry["path"])) == files.fingerprint(info)
        assert root.read(entry["path"], maximum=1024)[0] == data
        assert not root.exists("missing.pdf")
        with pytest.raises(files.FileError, match="DIRECTORY_LIMIT"):
            inventory.scan(root, "", maximum=2)
        with pytest.raises(files.FileError, match="LIMIT_EXCEEDED"):
            root.read(entry["path"], maximum=1)
    path.write_bytes(b"changed source")
    with files.source_root(tmp_path) as root, pytest.raises(files.FileError, match="SOURCE_CHANGED"):
        inventory.read_hash(root, entry["path"], maximum=1024, expected=entry["fingerprint"])


@windows
def test_native_stream_has_no_write_access_and_pins_path_until_closed(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    path = raw / "score.pdf"
    path.write_bytes(b"synthetic")
    with files.source_root(raw) as root, root.reader("score.pdf") as (descriptor, info):
        assert stat.S_ISREG(info.st_mode)
        assert not os.get_inheritable(descriptor)
        with pytest.raises(OSError):
            os.write(descriptor, b"modified")
        with pytest.raises(PermissionError):
            path.write_bytes(b"modified")
        with pytest.raises(PermissionError):
            path.rename(raw / "renamed.pdf")
        with pytest.raises(PermissionError):
            raw.rename(tmp_path / "moved")
        assert os.read(descriptor, 1024) == b"synthetic"
    raw.rename(tmp_path / "moved")
    assert (tmp_path / "moved" / "score.pdf").read_bytes() == b"synthetic"
    with pytest.raises(files.FileError, match="UNSAFE_ROOT"):
        root.root_metadata()


@windows
def test_native_reparses_and_hardlinks_are_never_trusted_sources(tmp_path):
    raw, outside = tmp_path / "raw", tmp_path / "outside"
    raw.mkdir()
    outside.mkdir()
    (outside / "score.pdf").write_bytes(b"outside synthetic")
    (raw / "linked").symlink_to(outside, target_is_directory=True)
    (raw / "linked.pdf").symlink_to(outside / "score.pdf")
    (raw / "hardlink.pdf").hardlink_to(outside / "score.pdf")
    with files.source_root(raw) as root:
        rows = inventory.scan(root, "")
        assert {row["path"] for row in rows if row["kind"] == "UNSAFE"} == {"linked", "linked.pdf", "hardlink.pdf"}
        for path in ("linked/score.pdf", "linked.pdf", "hardlink.pdf"):
            with pytest.raises(files.FileError):
                root.read(path, maximum=1024)
    with pytest.raises(files.FileError), files.source_root(raw / "linked"):
        pass
    assert (outside / "score.pdf").read_bytes() == b"outside synthetic"


@windows
@pytest.mark.parametrize("path", ["score.pdf:alternate", "score.pdf.", "CON.txt", "nested/../score.pdf"])
def test_native_namespace_aliases_are_rejected_before_opening(tmp_path, path):
    (tmp_path / "score.pdf").write_bytes(b"synthetic")
    with files.source_root(tmp_path) as root, pytest.raises((files.FileError, ValueError)):
        root.read(path, maximum=1024)
    assert [path.name for path in tmp_path.iterdir()] == ["score.pdf"]


@windows
def test_native_directory_mutation_invalidates_inventory(tmp_path):
    with (
        files.source_root(tmp_path) as root,
        pytest.raises(files.FileError, match="SOURCE_CHANGED"),
        root.directory_entries("") as (_, entries),
    ):
        assert list(entries) == []
        (tmp_path / "added.pdf").write_bytes(b"synthetic")


@windows
@pytest.mark.parametrize("inspect_security", [False, True])
def test_native_initialization_failure_releases_all_pinned_directories(tmp_path, monkeypatch, inspect_security):
    from core.files_windows import WindowsSourceRoot, kernel

    raw = tmp_path / "raw"
    raw.mkdir()
    monkeypatch.setattr(kernel(), "GetVolumeInformationByHandleW", lambda *_: 0)
    root = WindowsSourceRoot(raw, inspect_security=inspect_security)
    with pytest.raises(files.FileError, match="FILE_IO"), root:
        pass
    assert root._stack is None and root._handle is None
    raw.rename(tmp_path / "moved")
    assert (tmp_path / "moved").is_dir()


@pytest.mark.parametrize("flag", [None, 1, "true"])
def test_security_inspection_mode_requires_explicit_boolean(tmp_path, flag):
    from core.files_windows import WindowsSourceRoot

    with pytest.raises(files.FileError, match="UNSAFE_ROOT"):
        WindowsSourceRoot(tmp_path, inspect_security=flag)


@windows
@pytest.mark.parametrize("inspect_security", [False, True])
def test_native_security_inspection_rights_only_on_initial_directory_pins(tmp_path, monkeypatch, inspect_security):
    from core.files_windows import WindowsSourceRoot, kernel

    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "score.pdf").write_bytes(b"synthetic")
    api = kernel()
    original = api.CreateFileW
    calls = []

    def create(*args):
        calls.append(args)
        return original(*args)

    monkeypatch.setattr(api, "CreateFileW", create)
    with WindowsSourceRoot(raw, inspect_security=inspect_security) as root:
        initial = list(calls)
        assert len(initial) == len(raw.parts)
        for args in initial:
            assert args[1:] == (0x20081 if inspect_security else 0x81, 3, None, 3, 0x02200000, None)
        assert root.writable is False
        with pytest.raises(PermissionError):
            raw.rename(tmp_path / "moved")
        with root.reader("score.pdf") as (descriptor, _):
            assert not os.get_inheritable(descriptor)
            with pytest.raises(OSError):
                os.write(descriptor, b"modified")
        assert calls[len(initial)][1:] == (0x80000000, 1, None, 3, 0x02200000, None)
    raw.rename(tmp_path / "moved")


@windows
def test_native_root_reentry_is_rejected_without_losing_the_first_handle(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    with files.source_root(raw) as root:
        with pytest.raises(files.FileError, match="UNSAFE_ROOT"):
            root.__enter__()
        with pytest.raises(PermissionError):
            raw.rename(tmp_path / "moved")
    raw.rename(tmp_path / "moved")


@windows
def test_native_source_does_not_enable_unverified_writable_operations(tmp_path):
    with pytest.raises(files.FileError, match="UNSUPPORTED_FILESYSTEM_API"), files.Root(tmp_path, writable=True):
        pass
    with pytest.raises(files.FileError), files.source_root(tmp_path / "missing"):
        pass
    assert list(tmp_path.iterdir()) == []


@windows
def test_replaced_child_directory_cannot_redirect_a_later_source_read(tmp_path):
    raw, outside = tmp_path / "raw", tmp_path / "outside"
    raw.mkdir()
    outside.mkdir()
    (raw / "nested").mkdir()
    (raw / "nested" / "score.pdf").write_bytes(b"expected synthetic")
    (outside / "score.pdf").write_bytes(b"foreign synthetic")
    with files.source_root(raw) as root:
        (raw / "nested").rename(raw / "original")
        (raw / "nested").symlink_to(outside, target_is_directory=True)
        with pytest.raises(files.FileError):
            root.read("nested/score.pdf", maximum=1024)
        assert root.read("original/score.pdf", maximum=1024)[0] == b"expected synthetic"
    assert (outside / "score.pdf").read_bytes() == b"foreign synthetic"


@windows
def test_native_metadata_preserves_ntfs_timestamp_precision_and_hardlink_identity(tmp_path):
    path = tmp_path / "score.pdf"
    path.write_bytes(b"synthetic")
    (tmp_path / "alias.pdf").hardlink_to(path)
    timestamp = 1_700_000_000_123_456_700
    os.utime(path, ns=(timestamp, timestamp))
    with files.source_root(tmp_path) as root:
        before = root.metadata("score.pdf")
        assert before.st_mtime_ns == timestamp
        assert files.identity(before) == files.identity(root.metadata("alias.pdf"))
        os.utime(path, ns=(timestamp + 100, timestamp + 100))
        assert root.metadata("score.pdf").st_mtime_ns == timestamp + 100


@windows
def test_native_junction_leaf_and_ancestor_are_rejected(tmp_path):
    raw, outside = tmp_path / "raw", tmp_path / "outside"
    raw.mkdir()
    outside.mkdir()
    (outside / "score.pdf").write_bytes(b"foreign synthetic")
    linked = raw / "linked"
    junction(linked, outside)
    try:
        with files.source_root(raw) as root:
            rows = inventory.scan(root, "")
            assert next(row for row in rows if row["path"] == "linked")["kind"] == "UNSAFE"
            with pytest.raises(files.FileError):
                root.read("linked/score.pdf", maximum=1024)
        with pytest.raises(files.FileError), files.source_root(linked):
            pass
        assert (outside / "score.pdf").read_bytes() == b"foreign synthetic"
    finally:
        linked.rmdir()


@windows
def test_native_child_junction_replacement_cannot_redirect_read(tmp_path):
    raw, outside = tmp_path / "raw", tmp_path / "outside"
    raw.mkdir()
    outside.mkdir()
    nested = raw / "nested"
    nested.mkdir()
    (nested / "score.pdf").write_bytes(b"expected synthetic")
    (outside / "score.pdf").write_bytes(b"foreign synthetic")
    with files.source_root(raw) as root:
        nested.rename(raw / "original")
        junction(nested, outside)
        try:
            with pytest.raises(files.FileError):
                root.read("nested/score.pdf", maximum=1024)
            assert root.read("original/score.pdf", maximum=1024)[0] == b"expected synthetic"
        finally:
            nested.rmdir()
    assert (outside / "score.pdf").read_bytes() == b"foreign synthetic"
