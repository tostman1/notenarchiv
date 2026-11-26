"""Actual isolated Linux parser scratch cleanup under dead-worker ownership."""

import os

import pytest

from core import files
from core.pdf.recovery import PARSER_ACTIVE_MARKER, prune, prune_disposable

pytestmark = pytest.mark.skipif(os.name != "posix", reason="Descriptor-relative scratch cleanup requires POSIX")


def test_prune_removes_only_owned_abandoned_parser_files(tmp_path):
    directory = tmp_path / ".staging/generation/pdf-synthetic"
    directory.mkdir(mode=0o700, parents=True)
    (tmp_path / ".staging").chmod(0o700)
    (tmp_path / ".staging/generation").chmod(0o700)
    for name in ("0.pdf", "request.json", "response.json", "output"):
        (directory / name).write_bytes(b"Synthetic scratch")
    with files.Root(tmp_path, writable=True) as root:
        prune(root, ".staging/generation")
    assert not directory.exists()


def test_prune_refuses_links_and_unknown_files_without_following_them(tmp_path):
    directory = tmp_path / ".staging/generation/pdf-synthetic"
    directory.mkdir(mode=0o700, parents=True)
    (tmp_path / ".staging").chmod(0o700)
    (tmp_path / ".staging/generation").chmod(0o700)
    protected = tmp_path / "historical.pdf"
    protected.write_bytes(b"Synthetic retained history")
    (directory / "0.pdf").symlink_to(protected)
    with files.Root(tmp_path, writable=True) as root, pytest.raises(files.FileError):
        prune(root, ".staging/generation")
    assert protected.read_bytes() == b"Synthetic retained history"


def test_disposable_cleanup_warns_and_preserves_unknown_entries(tmp_path, caplog):
    with files.Root(tmp_path, writable=True) as root:
        root.prepare_parent(".staging/generation/pdf-synthetic/placeholder")
        workspace = tmp_path / ".staging/generation/pdf-synthetic"
        evidence = workspace / "other"
        evidence.write_bytes(b"Unknown evidence")
        prune_disposable(root, ".staging/generation")

    assert evidence.read_bytes() == b"Unknown evidence"
    assert "Could not safely prune disposable PDF processing workspaces" in caplog.text


def test_prune_preserves_workspace_if_parser_stop_is_unproven(tmp_path):
    with files.Root(tmp_path, writable=True) as root:
        root.prepare_parent(".staging/generation/pdf-synthetic/placeholder")
        workspace = tmp_path / ".staging/generation/pdf-synthetic"
        (workspace / PARSER_ACTIVE_MARKER).touch()
        (workspace / "0.pdf").write_bytes(b"Synthetic parser input")
        prune(root, ".staging/generation")

    assert (workspace / "0.pdf").read_bytes() == b"Synthetic parser input"
