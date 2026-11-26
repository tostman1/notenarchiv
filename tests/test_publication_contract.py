"""Platform-independent publication policy and backend dispatch contracts."""

import hashlib
from types import SimpleNamespace
from unittest.mock import ANY, Mock, call

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


def test_pending_verification_dispatches_proof_before_inspection_and_durability():
    root = backend()
    data = b"synthetic"
    final = metadata(links=2)
    root.read.return_value = data, final
    processor = Mock()
    root.attach_mock(processor, "processor")
    digest = hashlib.sha256(data).hexdigest()
    assert files.verify_published(
        root, "score.pdf", sha256=digest, size=9, staged_path=STAGED, processor=processor, durable=True
    ) == (
        data,
        final,
    )
    assert root.mock_calls == [
        call.read("score.pdf", maximum=9, checkpoint=ANY, links=2),
        call.verify_publication_proof("score.pdf", final, staged_path=STAGED),
        call.processor.inspect(data),
        call.verify_entry("score.pdf"),
        call.durable_entry("score.pdf", final, staged_path=STAGED),
    ]


# Failure contracts of the shared verify/release entrypoints. These mock-backed
# contracts fix the dispatch policy on both platforms; they do not prove native
# power-loss durability or independent RAW isolation, and no cleanup/release may
# follow a failed verification.


def verify(root, **overrides):
    kwargs = dict(
        sha256=hashlib.sha256(b"synthetic").hexdigest(),
        size=9,
        staged_path=STAGED,
        processor=Mock(),
        checkpoint=Mock(),
        durable=True,
    )
    kwargs.update(overrides)
    return files.verify_published(root, "score.pdf", **kwargs)


def test_verified_failure_propagates_before_durable_acknowledgement():
    """A backend durability failure propagates unchanged; there is no successful return.

    The barrier is the last effect the shared contract attempts, so the original
    call history (not a reset) is asserted: the barrier was reached once and no
    cleanup/release dispatch ever followed."""
    data = b"synthetic"
    final = metadata(links=2)
    root = backend()
    root.read.return_value = data, final
    root.durable_entry.side_effect = files.FileError("STAGING_CHANGED")
    with pytest.raises(files.FileError, match="STAGING_CHANGED"):
        verify(root)
    root.durable_entry.assert_called_once_with("score.pdf", final, staged_path=STAGED)
    # Original history: no cleanup or release dispatch follows a failed verification.
    root.release_stage.assert_not_called()
    root.discard_stage.assert_not_called()


@pytest.mark.parametrize(
    ("override", "error"),
    [
        ({"size": 10}, "COPY_MISMATCH"),  # expected size no longer matches published bytes
        ({"sha256": "0" * 64}, "COPY_MISMATCH"),  # published bytes no longer match digest
    ],
    ids=["byte-size", "byte-digest"],
)
def test_byte_proof_fails_before_durable_acknowledgement(override, error):
    """Byte checks run before retained-identity proof and any durable acknowledgement."""
    root = backend()
    root.read.return_value = b"synthetic", metadata(links=2)
    with pytest.raises(files.FileError, match=error):
        verify(root, **override)
    root.verify_publication_proof.assert_not_called()
    root.verify_entry.assert_not_called()
    root.durable_entry.assert_not_called()
    root.release_stage.assert_not_called()


@pytest.mark.parametrize("error", [files.FileError("PUBLICATION_CONFLICT"), FileNotFoundError(STAGED)])
def test_backend_proof_error_propagates_before_inspection_and_durability(error):
    root = backend()
    final = metadata(links=2)
    root.read.return_value = b"synthetic", final
    root.verify_publication_proof.side_effect = error
    processor = Mock()
    with pytest.raises(type(error)) as caught:
        verify(root, processor=processor)
    assert caught.value is error
    root.verify_publication_proof.assert_called_once_with("score.pdf", final, staged_path=STAGED)
    processor.inspect.assert_not_called()
    root.durable_entry.assert_not_called()
    root.verify_entry.assert_not_called()
    root.release_stage.assert_not_called()


def test_reader_error_propagates_with_pending_link_budget():
    """Dispatch the pending link budget and propagate a supplied reader error.

    The mock does not establish native external-hardlink rejection.
    """
    root = backend()
    root.read.side_effect = files.FileError("UNSAFE_FILE")
    with pytest.raises(files.FileError, match="UNSAFE_FILE"):
        verify(root)
    root.read.assert_called_once_with("score.pdf", maximum=9, checkpoint=ANY, links=2)
    root.verify_publication_proof.assert_not_called()
    root.durable_entry.assert_not_called()
    root.verify_entry.assert_not_called()
    root.release_stage.assert_not_called()


def test_invalid_staging_reference_fails_before_backend_proof():
    root = backend()
    data = b"synthetic"
    final = metadata(links=2)
    root.read.return_value = data, final
    with pytest.raises(files.FileError, match="UNSAFE_STAGING"):
        verify(root, staged_path="score.pdf")
    root.verify_publication_proof.assert_not_called()
    root.durable_entry.assert_not_called()
    root.verify_entry.assert_not_called()
    root.release_stage.assert_not_called()


def test_unwritable_backend_fails_closed_at_durable_barrier():
    """durable=True on a non-writable backend raises before any durable effect."""
    data = b"synthetic"
    final = metadata(links=2)
    root = backend(writable=False)
    root.read.return_value = data, final
    with pytest.raises(files.FileError, match="READ_ONLY_ROOT"):
        verify(root)
    root.durable_entry.assert_not_called()
    root.verify_entry.assert_called_once_with("score.pdf")
    root.release_stage.assert_not_called()


def test_non_durable_verification_skips_backend_barrier():
    """durable=False never invokes the backend durability barrier."""
    data = b"synthetic"
    final = metadata(links=2)
    root = backend()
    root.read.return_value = data, final
    assert verify(root, durable=False) == (data, final)
    root.durable_entry.assert_not_called()
    root.verify_entry.assert_called_once_with("score.pdf")
    root.release_stage.assert_not_called()


def test_temporary_cleanup_dispatch_requires_valid_staging_reference():
    root = backend()
    files.discard_stage(root, STAGED, (1, 7))
    files.release_stage(root, STAGED, "score.pdf")
    root.discard_stage.assert_called_once_with(STAGED, (1, 7))
    root.release_stage.assert_called_once_with(STAGED, "score.pdf")
    with pytest.raises(files.FileError, match="UNSAFE_STAGING"):
        files.discard_stage(root, "score.pdf", (1, 7))
    root.discard_stage.assert_called_once()


def test_verification_without_stage_skips_backend_proof_and_uses_single_link_budget():
    root = backend()
    final = metadata()
    root.read.return_value = b"synthetic", final
    assert verify(root, staged_path=None) == (b"synthetic", final)
    root.read.assert_called_once_with("score.pdf", maximum=9, checkpoint=ANY, links=1)
    root.verify_publication_proof.assert_not_called()
    root.durable_entry.assert_called_once_with("score.pdf", final, staged_path=None)


def test_posix_publication_proof_accepts_matching_regular_stage_without_extra_checks(tmp_path):
    root = files.Root(tmp_path)
    # No filesystem entry or POSIX API is used: exercise the actual backend method.
    staged = metadata(links=1)
    root.metadata = Mock(return_value=staged)
    assert root.verify_publication_proof("score.pdf", metadata(links=2), staged_path=STAGED) is None
    root.metadata.assert_called_once_with(STAGED)


@pytest.mark.parametrize("change", ["inode", "volume", "directory", "symlink", "one-link", "three-links"])
def test_posix_publication_proof_rejects_conflicts(tmp_path, change):
    root = files.Root(tmp_path)
    staged, final = metadata(), metadata(links=2)
    if change == "inode":
        staged.st_ino += 1
    elif change == "volume":
        staged.st_dev += 1
    elif change == "directory":
        staged.st_mode = 0o040700
    elif change == "symlink":
        staged.st_mode = 0o120700
    else:
        final.st_nlink = 1 if change == "one-link" else 3
    root.metadata = Mock(return_value=staged)
    with pytest.raises(files.FileError, match="PUBLICATION_CONFLICT"):
        root.verify_publication_proof("score.pdf", final, staged_path=STAGED)
    root.metadata.assert_called_once_with(STAGED)


def test_posix_publication_proof_propagates_missing_stage(tmp_path):
    root = files.Root(tmp_path)
    error = FileNotFoundError(STAGED)
    root.metadata = Mock(side_effect=error)
    with pytest.raises(FileNotFoundError) as caught:
        root.verify_publication_proof("score.pdf", metadata(links=2), staged_path=STAGED)
    assert caught.value is error
    root.metadata.assert_called_once_with(STAGED)
