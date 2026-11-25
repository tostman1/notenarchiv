"""Known-marker replacement and uncertain effects at the POSIX backend boundary."""

import os

import pytest

from core import files

pytestmark = pytest.mark.skipif(os.name != "posix", reason="POSIX marker publication backend")
FIRST = ".staging/" + "1" * 32 + "/attempt-1.pdf"
SECOND = ".staging/" + "2" * 32 + "/attempt-1.pdf"
TARGET = "folder/INDEXSTATUS.json"


def initial(root):
    info = root.write_stage(FIRST, [b"first"], maximum=64)
    root.prepare_parent(TARGET)
    root.publish_marker(FIRST, TARGET, expected_identity=files.identity(info), previous=None, temporary=".marker-first")
    files.release_stage(root, FIRST, TARGET)
    return files.fingerprint(root.metadata(TARGET))


def test_marker_create_and_known_replacement_preserve_verified_staging_identity(tmp_path):
    with files.Root(tmp_path, writable=True) as root:
        previous = initial(root)
        info = root.write_stage(SECOND, [b"second"], maximum=64)
        root.publish_marker(
            SECOND, TARGET, expected_identity=files.identity(info), previous=previous, temporary=".marker-second"
        )
        assert files.identity(root.metadata(TARGET)) == files.identity(info)
        files.release_stage(root, SECOND, TARGET)
        assert root.read(TARGET, maximum=64)[0] == b"second"


def test_changed_marker_is_retained_and_music_target_is_rejected(tmp_path):
    with files.Root(tmp_path, writable=True) as root:
        previous = initial(root)
        info = root.write_stage(SECOND, [b"second"], maximum=64)
        target = tmp_path / TARGET
        target.chmod(0o600)
        target.write_bytes(b"foreign")
        target.chmod(0o440)
        with pytest.raises(files.MarkerConflict, match="MARKER_CHANGED"):
            root.publish_marker(
                SECOND, TARGET, expected_identity=files.identity(info), previous=previous, temporary=".marker-second"
            )
        assert target.read_bytes() == b"foreign"
        with pytest.raises(files.FileError, match="UNSAFE_DESTINATION"):
            root.publish_marker(
                SECOND, "score.pdf", expected_identity=files.identity(info), previous=None, temporary=".marker-second"
            )
        assert not root.exists("score.pdf")


def test_replacement_io_error_is_not_reported_as_a_proven_no_effect(tmp_path, monkeypatch):
    with files.Root(tmp_path, writable=True) as root:
        previous = initial(root)
        info = root.write_stage(SECOND, [b"second"], maximum=64)

        def uncertain(*args, **kwargs):
            raise FileExistsError("Synthetic uncertain replacement")

        monkeypatch.setattr(files.os, "replace", uncertain)
        with pytest.raises(FileExistsError, match="Synthetic uncertain replacement"):
            root.publish_marker(
                SECOND, TARGET, expected_identity=files.identity(info), previous=previous, temporary=".marker-second"
            )
        assert root.read(TARGET, maximum=64)[0] == b"first"
        assert root.metadata(SECOND).st_nlink == 2
