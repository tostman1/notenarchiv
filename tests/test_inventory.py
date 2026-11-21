"""Core RAW traversal bounds, stability and read-only descriptor access."""

import os

import pytest

from core import files, inventory

pytestmark = pytest.mark.skipif(os.name != "posix", reason="POSIX anchored inventory APIs required")


def test_inventory_bounds_never_follow_links_and_hashes_stable_bytes(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "nested").mkdir()
    (raw / "nested" / "input.pdf").write_bytes(b"synthetic")
    (raw / "link").symlink_to(raw / "nested", target_is_directory=True)
    with files.Root(raw) as root:
        rows = inventory.scan(root, "")
        assert len(rows) == 4 and next(row for row in rows if row["path"] == "link")["kind"] == "UNSAFE"
        with pytest.raises(files.FileError, match="DIRECTORY_LIMIT"):
            inventory.scan(root, "", maximum=2)
        entry = next(row for row in rows if row["path"] == "nested/input.pdf")
        digest, data, info = inventory.read_hash(root, entry["path"], maximum=1024, expected=entry["fingerprint"])
        assert data == b"synthetic" and len(digest) == 64 and info.st_size == len(data)
        (raw / "nested" / "input.pdf").write_bytes(b"different")
        with pytest.raises(files.FileError, match="SOURCE_CHANGED"):
            inventory.read_hash(root, entry["path"], maximum=1024, expected=entry["fingerprint"])


def test_source_mutation_during_stream_is_rejected(tmp_path):
    (tmp_path / "input.pdf").write_bytes(b"synthetic")
    with files.Root(tmp_path) as root:

        def mutate():
            (tmp_path / "input.pdf").write_bytes(b"changed")

        with pytest.raises(files.FileError, match="SOURCE_CHANGED"):
            inventory.read_hash(root, "input.pdf", maximum=1024, checkpoint=mutate)
