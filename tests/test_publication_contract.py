"""Platform-independent publication policy and backend dispatch contracts."""

import hashlib
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from core import files

STAGED = ".staging/" + "1" * 32 + "/attempt-1.pdf"


def metadata(*, inode=7, links=1):
    return SimpleNamespace(
        st_dev=1, st_ino=inode, st_mode=0o100400, st_nlink=links, st_size=9, st_mtime_ns=100, st_ctime_ns=200
    )


def backend(*, writable=True):
    root = Mock(writable=writable)
    root.directory_spelling.side_effect = lambda path: path
    root.collides.return_value = False
    return root


def test_publication_dispatch_preserves_no_clobber_and_staging_policy():
    root = backend()
    stage = files.Stage(STAGED, metadata(), "a" * 64, 9)
    files.publish(root, stage, "nested/score.pdf")
    root.publish_stage.assert_called_once_with(stage, "nested/score.pdf")
    for path in (".staging/score.pdf", "../score.pdf"):
        with pytest.raises(ValueError):
            files.publish(root, stage, path)
    root.publish_stage.assert_called_once()


@pytest.mark.parametrize("conflict", ["collision", "spelling"])
def test_publication_conflicts_never_reach_effect_boundary(conflict):
    root = backend()
    if conflict == "collision":
        root.collides.return_value = True
    else:
        root.directory_spelling.side_effect = None
        root.directory_spelling.return_value = "Nested/score.pdf"
    with pytest.raises(files.FileError, match="DESTINATION_EXISTS"):
        files.publish(root, files.Stage(STAGED, metadata(), "a" * 64, 9), "nested/score.pdf")
    root.publish_stage.assert_not_called()


@pytest.mark.parametrize("operation", ["discard", "release", "publish"])
def test_read_only_root_cannot_enter_mutating_backend(operation):
    root = backend(writable=False)
    with pytest.raises(files.FileError):
        if operation == "discard":
            files.discard_stage(root, STAGED, (1, 7))
        elif operation == "release":
            files.release_stage(root, STAGED, "score.pdf")
        else:
            files.publish(root, files.Stage(STAGED, metadata(), "a" * 64, 9), "score.pdf")
    root.discard_stage.assert_not_called()
    root.release_stage.assert_not_called()
    root.publish_stage.assert_not_called()


def test_pending_verification_requires_retained_identity_before_durable_acknowledgement():
    root = backend()
    data = b"synthetic"
    final = metadata(links=2)
    root.read.return_value = data, final
    root.metadata.return_value = metadata()
    digest = hashlib.sha256(data).hexdigest()
    assert files.verify_published(root, "score.pdf", sha256=digest, size=9, staged_path=STAGED, durable=True) == (
        data,
        final,
    )
    root.verify_entry.assert_called_once_with("score.pdf")
    root.durable_entry.assert_called_once_with("score.pdf", final, staged_path=STAGED)
    root.reset_mock()
    root.metadata.return_value = metadata(inode=8)
    with pytest.raises(files.FileError, match="PUBLICATION_CONFLICT"):
        files.verify_published(root, "score.pdf", sha256=digest, size=9, staged_path=STAGED, durable=True)
    root.durable_entry.assert_not_called()


def test_temporary_cleanup_dispatch_requires_valid_staging_reference():
    root = backend()
    files.discard_stage(root, STAGED, (1, 7))
    files.release_stage(root, STAGED, "score.pdf")
    root.discard_stage.assert_called_once_with(STAGED, (1, 7))
    root.release_stage.assert_called_once_with(STAGED, "score.pdf")
    with pytest.raises(files.FileError, match="UNSAFE_STAGING"):
        files.discard_stage(root, "score.pdf", (1, 7))
    root.discard_stage.assert_called_once()
