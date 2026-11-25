"""Backup traversal policy is independent of platform directory handles."""

import stat

import pytest

from core import backup
from tests.test_inventory_contract import MetadataRoot, metadata


def test_backup_inventory_reuses_metadata_boundary_and_preserves_exclusions():
    root = MetadataRoot(
        {
            "": (metadata(1), [("folder", metadata(2)), ("ignored", metadata(3, stat.S_IFLNK))]),
            "folder": (metadata(2), [("music.pdf", metadata(4, stat.S_IFREG, links=2))]),
        }
    )
    budget = backup.Budget(backup.DEFAULT_LIMITS)
    assert list(backup.inventory(root, budget, excluded=("ignored",))) == ["folder/music.pdf"]
    assert budget.count == 2 and budget.size == 9


@pytest.mark.parametrize("kind", ["replaced", "mutated", "unsafe"])
def test_backup_inventory_rejects_changed_or_unsafe_metadata(kind):
    root = MetadataRoot(
        {
            "": (metadata(1), [("folder", metadata(2))]),
            "folder": (metadata(99 if kind == "replaced" else 2), [("input", metadata(4, stat.S_IFREG, links=3))]),
        },
        changed=kind == "mutated",
    )
    if kind == "mutated":
        root = MetadataRoot({"": (metadata(1), [])}, changed=True)
    expected = "UNSAFE_BACKUP_FILE" if kind == "unsafe" else "BACKUP_CHANGED"
    with pytest.raises(backup.BackupError, match=expected):
        list(backup.inventory(root, backup.Budget(backup.DEFAULT_LIMITS)))
