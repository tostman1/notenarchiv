"""Real POSIX copy, mutation, collision, symlink and interruption safety tests."""

import hashlib
import os
from contextlib import ExitStack

import pytest

from core import files
from core.pdf import Limits, PdfError, Processor
from tests.pdf_fixtures import pdf

pytestmark = pytest.mark.skipif(os.name != "posix", reason="Physical publication requires POSIX dir-fd/no-follow APIs")
STAGED = ".staging/" + "1" * 32 + "/attempt-1.pdf"


@pytest.fixture
def copy_inputs(tmp_path):
    raw, clean, scratch = [tmp_path / name for name in ("raw", "clean", "scratch")]
    for directory in (raw, clean, scratch):
        directory.mkdir(mode=0o700)
    data = pdf()
    (raw / "correct.pdf").write_bytes(data)
    processor = Processor(scratch, limits=Limits(max_bytes=4_194_304, memory_bytes=268_435_456))
    with ExitStack() as stack:
        source = stack.enter_context(files.Root(raw))
        destination = stack.enter_context(files.Root(clean, writable=True))
        yield source, destination, processor, data


def stage(inputs, **kwargs):
    source, destination, processor, data = inputs
    return files.stage_copy(
        source,
        "correct.pdf",
        destination,
        STAGED,
        sha256=hashlib.sha256(data).hexdigest(),
        size=len(data),
        processor=processor,
        **kwargs,
    )


def test_correctly_named_source_is_an_independent_real_verified_copy(copy_inputs):
    source, destination, _processor, data = copy_inputs
    before = source.metadata("correct.pdf")
    prepared = stage(copy_inputs)
    files.publish(destination, prepared, "correct.pdf")
    assert (destination.path / "correct.pdf").read_bytes() == data
    assert files.identity(before) != files.identity(destination.metadata("correct.pdf"))
    assert source.metadata("correct.pdf").st_mtime_ns == before.st_mtime_ns
    assert destination.metadata("correct.pdf").st_nlink == 2
    verified, _ = files.verify_published(
        destination, "correct.pdf", sha256=prepared.sha256, size=prepared.size, staged_path=STAGED
    )
    assert verified == data
    files.release_stage(destination, STAGED, "correct.pdf")
    assert destination.metadata("correct.pdf").st_nlink == 1 and not destination.exists(STAGED)
    assert (source.path / "correct.pdf").read_bytes() == data


@pytest.mark.parametrize("same_bytes", [False, True])
def test_existing_destination_is_never_overwritten_even_with_equal_bytes(copy_inputs, same_bytes):
    _source, destination, _processor, data = copy_inputs
    existing = data if same_bytes else b"Synthetic unrelated history"
    (destination.path / "correct.pdf").write_bytes(existing)
    prepared = stage(copy_inputs)
    with pytest.raises(files.FileError, match="DESTINATION_EXISTS"):
        files.publish(destination, prepared, "correct.pdf")
    assert (destination.path / "correct.pdf").read_bytes() == existing
    assert destination.exists(STAGED)


def test_case_collisions_and_repeated_directory_scans_are_detected(copy_inputs):
    _source, destination, _processor, _data = copy_inputs
    (destination.path / "CORRECT.PDF").write_bytes(b"Synthetic other case")
    for _ in range(3):
        assert destination.collides("correct.pdf")
    prepared = stage(copy_inputs)
    with pytest.raises(files.FileError, match="DESTINATION_EXISTS"):
        files.publish(destination, prepared, "correct.pdf")
    assert not destination.exists("correct.pdf")


def test_external_mutation_during_copy_is_detected_and_unpublished(copy_inputs):
    source, destination, _processor, data = copy_inputs
    changed = False

    def external_change():
        nonlocal changed
        if not changed:
            # The fixture acts as a separate source owner, not application code.
            (source.path / "correct.pdf").write_bytes(data[:-1] + b" ")
            changed = True

    with pytest.raises(files.FileError, match="SOURCE_CHANGED"):
        stage(copy_inputs, checkpoint=external_change)
    assert changed and not destination.exists(STAGED) and not destination.exists("correct.pdf")


@pytest.mark.parametrize("path", ["../escape.pdf", "/escape.pdf", "nested/../../escape.pdf", "x\\escape.pdf"])
def test_traversal_is_rejected_before_source_access(copy_inputs, path):
    source, destination, processor, data = copy_inputs
    with pytest.raises(ValueError):
        files.stage_copy(
            source,
            path,
            destination,
            STAGED,
            sha256=hashlib.sha256(data).hexdigest(),
            size=len(data),
            processor=processor,
        )
    assert not destination.exists(STAGED)


@pytest.mark.parametrize("where", ["source", "source_parent", "destination_parent", "staging", "root"])
def test_symlink_components_never_escape_configured_roots(copy_inputs, tmp_path, where):
    source, destination, processor, data = copy_inputs
    outside = tmp_path / "outside"
    outside.mkdir()
    outside_file = outside / "correct.pdf"
    outside_file.write_bytes(data)
    if where == "source":
        (source.path / "correct.pdf").unlink()
        (source.path / "correct.pdf").symlink_to(outside_file)
    elif where == "source_parent":
        (source.path / "linked").symlink_to(outside, target_is_directory=True)
        with pytest.raises(files.FileError), source.reader("linked/correct.pdf"):
            pytest.fail("Symlinked parent must be refused")
        return
    elif where == "destination_parent":
        prepared = stage(copy_inputs)
        (destination.path / "linked").symlink_to(outside, target_is_directory=True)
        with pytest.raises((files.FileError, OSError)):
            files.publish(destination, prepared, "linked/correct.pdf")
        assert list(outside.iterdir()) == [outside_file]
        return
    elif where == "staging":
        (destination.path / ".staging").symlink_to(outside, target_is_directory=True)
    else:
        linked = tmp_path / "linked-root"
        linked.symlink_to(outside, target_is_directory=True)
        with pytest.raises(files.FileError, match="UNSAFE_ROOT"), files.Root(linked):
            pytest.fail("Symlinked root must be refused")
        return
    with pytest.raises(files.FileError):
        files.stage_copy(
            source,
            "correct.pdf",
            destination,
            STAGED,
            sha256=hashlib.sha256(data).hexdigest(),
            size=len(data),
            processor=processor,
        )
    assert list(outside.iterdir()) == [outside_file]
    assert outside_file.read_bytes() == data


def test_fifo_and_hardlinked_sources_are_refused_without_reading(copy_inputs):
    source, destination, _processor, _data = copy_inputs
    (source.path / "correct.pdf").unlink()
    os.mkfifo(source.path / "correct.pdf")
    with pytest.raises(files.FileError, match="UNSAFE_FILE"):
        stage(copy_inputs)
    (source.path / "correct.pdf").unlink()
    target = source.path / "other.pdf"
    target.write_bytes(b"Synthetic hard link")
    os.link(target, source.path / "correct.pdf")
    with pytest.raises(files.FileError, match="UNSAFE_FILE"):
        stage(copy_inputs)
    assert not destination.exists(STAGED)


def test_invalid_pdf_and_resource_limits_leave_no_publishable_stage(copy_inputs):
    source, destination, processor, _data = copy_inputs
    invalid = b"Synthetic invalid PDF"
    (source.path / "correct.pdf").write_bytes(invalid)
    with pytest.raises(PdfError):
        files.stage_copy(
            source,
            "correct.pdf",
            destination,
            STAGED,
            sha256=hashlib.sha256(invalid).hexdigest(),
            size=len(invalid),
            processor=processor,
        )
    assert not destination.exists(STAGED)
    with pytest.raises(files.FileError, match="LIMIT_EXCEEDED"):
        files.stage_copy(
            source,
            "correct.pdf",
            destination,
            STAGED,
            sha256="0" * 64,
            size=processor.limits.max_bytes + 1,
            processor=processor,
        )


def test_short_writes_are_completed_and_independent_readback_detects_corruption(copy_inputs, monkeypatch):
    source, destination, _processor, data = copy_inputs
    real_write = os.write
    monkeypatch.setattr(files.os, "write", lambda descriptor, buffer: real_write(descriptor, buffer[:7]))
    prepared = stage(copy_inputs)
    assert (destination.path / STAGED).read_bytes() == data
    files.discard_stage(destination, STAGED, files.identity(prepared.info))
    real_read = files.Root.read

    def corrupt(root, path, **kwargs):
        copied, info = real_read(root, path, **kwargs)
        return copied[:-1] + b"!", info

    monkeypatch.setattr(files.Root, "read", corrupt)
    with pytest.raises(files.FileError, match="COPY_MISMATCH"):
        stage(copy_inputs)
    assert not destination.exists(STAGED) and (source.path / "correct.pdf").read_bytes() == data


def test_read_only_root_never_creates_staging(copy_inputs):
    source, destination, processor, data = copy_inputs
    with files.Root(destination.path) as readonly, pytest.raises(files.FileError, match="READ_ONLY_ROOT"):
        files.stage_copy(
            source,
            "correct.pdf",
            readonly,
            STAGED,
            sha256=hashlib.sha256(data).hexdigest(),
            size=len(data),
            processor=processor,
        )
    assert not (destination.path / ".staging").exists()


def test_copy_deadline_fails_closed_and_cleans_its_unlinked_stage(copy_inputs, monkeypatch):
    elapsed = iter([0, 2])
    monkeypatch.setattr(files.time, "monotonic", lambda: next(elapsed))
    with pytest.raises(files.FileError, match="COPY_TIMEOUT"):
        stage(copy_inputs, timeout=1)
    assert not copy_inputs[1].exists(STAGED)
