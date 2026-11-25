"""Inventory policy uses storage metadata independently of OS directory handles."""

import stat
from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from core import files, inventory


def metadata(inode, mode=stat.S_IFDIR, links=1):
    return SimpleNamespace(
        st_dev=1, st_ino=inode, st_mode=mode, st_nlink=links, st_size=9, st_mtime_ns=1, st_ctime_ns=1
    )


class MetadataRoot:
    def __init__(self, directories, *, changed=False):
        self.directories = directories
        self.changed = changed

    @contextmanager
    def directory_entries(self, path):
        yield self.directories[path]
        if self.changed:
            raise files.FileError("SOURCE_CHANGED")


def test_inventory_policy_accepts_metadata_without_os_handles():
    root = MetadataRoot(
        {
            "": (metadata(1), [("nested", metadata(2)), ("link", metadata(3, stat.S_IFLNK))]),
            "nested": (metadata(2), [("input.pdf", metadata(4, stat.S_IFREG))]),
        }
    )
    rows = inventory.scan(root, "")
    assert [(row["path"], row["kind"]) for row in rows] == [
        ("", "DIRECTORY"),
        ("link", "UNSAFE"),
        ("nested", "DIRECTORY"),
        ("nested/input.pdf", "FILE"),
    ]
    assert rows[-1]["fingerprint"] == [1, 4, 9, 1, 1]
    with pytest.raises(files.FileError, match="DIRECTORY_LIMIT"):
        inventory.scan(root, "", maximum=2)


def test_inventory_rejects_revisited_identity_and_changed_directory():
    root = MetadataRoot({"": (metadata(1), [("cycle", metadata(1))]), "cycle": (metadata(1), [])})
    with pytest.raises(files.FileError, match="DIRECTORY_CONFLICT"):
        inventory.scan(root, "")
    with pytest.raises(files.FileError, match="SOURCE_CHANGED"):
        inventory.scan(MetadataRoot({"": (metadata(1), [])}, changed=True), "")
