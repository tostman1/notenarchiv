"""Actual private-directory invariants at the POSIX filesystem boundary."""

import os
import stat

import pytest

from core import files

pytestmark = pytest.mark.skipif(os.name != "posix", reason="POSIX backend directory handles")


def test_root_metadata_and_private_directory_creation_are_backend_owned(tmp_path):
    with files.Root(tmp_path, writable=True) as root:
        assert files.identity(root.root_metadata()) == files.identity(tmp_path.stat())
        root.ensure_private_directory("scratch")
        root.ensure_private_directory("scratch")
        info = root.metadata("scratch")
        assert stat.S_ISDIR(info.st_mode)
        assert stat.S_IMODE(info.st_mode) == 0o700 and info.st_uid == os.geteuid()
    with pytest.raises(files.FileError, match="UNSAFE_ROOT"):
        root.root_metadata()


def test_readonly_root_never_initializes_private_directories(tmp_path):
    with files.Root(tmp_path) as root, pytest.raises(files.FileError, match="READ_ONLY_ROOT"):
        root.ensure_private_directory("scratch")
    assert list(tmp_path.iterdir()) == []


def test_existing_public_directory_is_rejected_without_permission_changes(tmp_path):
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    scratch.chmod(0o755)
    with files.Root(tmp_path, writable=True) as root, pytest.raises(files.FileError, match="UNSAFE_STAGING"):
        root.ensure_private_directory("scratch")
    assert stat.S_IMODE(scratch.stat().st_mode) == 0o755


def test_private_directory_never_follows_a_link(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (tmp_path / "scratch").symlink_to(outside, target_is_directory=True)
    with files.Root(tmp_path, writable=True) as root, pytest.raises(files.FileError, match="UNSAFE_ROOT"):
        root.ensure_private_directory("scratch")
    assert list(outside.iterdir()) == []
