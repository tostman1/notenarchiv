"""POSIX descriptor-anchored immutable copy/publication, without Django or RAW writes.

Fail closed on platforms without the required no-follow/dir-fd primitives. The
application targets Linux containers; Windows can exercise pure naming/metadata.
"""

import hashlib
import os
import re
import stat
import time
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from core.paths import relative_path, storage_key

CHUNK = 1_048_576


class FileError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def fingerprint(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def identity(info):
    return info.st_dev, info.st_ino


class Root:
    """A trusted existing root opened component-by-component without symlinks."""

    def __init__(self, path, *, writable=False):
        self.path, self.writable, self.fd = Path(path), writable, None

    def __enter__(self):
        required = (os.open, os.stat, os.mkdir, os.unlink, os.link)
        if os.name != "posix" or not all(fn in os.supports_dir_fd for fn in required):
            raise FileError("UNSUPPORTED_FILESYSTEM_API")
        if not self.path.is_absolute() or ".." in self.path.parts:
            raise FileError("UNSAFE_ROOT")
        descriptor = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
        try:
            for name in self.path.parts[1:]:
                following = os.open(name, self._directory_flags, dir_fd=descriptor)
                os.close(descriptor)
                descriptor = following
            self.fd = descriptor
        except OSError:
            os.close(descriptor)
            raise FileError("UNSAFE_ROOT") from None
        return self

    @property
    def _directory_flags(self):
        return os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC

    def __exit__(self, *exception):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None

    @contextmanager
    def parent(self, path, *, create=False):
        parts = PurePosixPath(relative_path(path)).parts
        if self.fd is None or len(parts) > 64 or (create and not self.writable):
            raise FileError("UNSAFE_PATH")
        descriptor = os.dup(self.fd)
        private = parts[0] == ".staging"
        try:
            for name in parts[:-1]:
                if create:
                    try:
                        os.mkdir(name, 0o700 if private else 0o750, dir_fd=descriptor)
                        os.fsync(descriptor)
                    except FileExistsError:
                        pass
                following = os.open(name, self._directory_flags, dir_fd=descriptor)
                os.close(descriptor)
                descriptor = following
                info = os.fstat(descriptor)
                if private and (info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o077):
                    raise FileError("UNSAFE_STAGING")
            yield descriptor, parts[-1]
        finally:
            os.close(descriptor)

    def metadata(self, path):
        with self.parent(path) as (parent, name):
            return os.stat(name, dir_fd=parent, follow_symlinks=False)

    @contextmanager
    def directory_entries(self, path):
        """Yield stable directory metadata and lazy no-follow child metadata."""
        path = relative_path(path, allow_root=True)
        reference = f"{path}/placeholder" if path else "placeholder"
        with self.parent(reference) as (descriptor, _):
            before = os.fstat(descriptor)
            with os.scandir(descriptor) as entries:
                yield (
                    before,
                    ((entry.name, os.stat(entry.name, dir_fd=descriptor, follow_symlinks=False)) for entry in entries),
                )
            if fingerprint(os.fstat(descriptor)) != fingerprint(before):
                raise FileError("SOURCE_CHANGED")

    def exists(self, path):
        try:
            self.metadata(path)
            return True
        except FileNotFoundError:
            return False

    def directory_spelling(self, path):
        """Reuse actual parent spelling; reject ambiguous SMB-equivalent entries."""
        parts = list(PurePosixPath(relative_path(path)).parts)
        descriptor = os.dup(self.fd)
        try:
            for index, requested in enumerate(parts[:-1]):
                matches = self._matching_names(descriptor, requested)
                if not matches:
                    break
                if len(matches) != 1:
                    raise FileError("PUBLICATION_CONFLICT")
                parts[index] = matches[0]
                following = os.open(parts[index], self._directory_flags, dir_fd=descriptor)
                os.close(descriptor)
                descriptor = following
            return str(PurePosixPath(*parts))
        finally:
            os.close(descriptor)

    def collides(self, path):
        try:
            with self.parent(path) as (parent, name):
                return bool(self._matching_names(parent, name))
        except FileNotFoundError:
            return False

    @staticmethod
    def _matching_names(descriptor, requested):
        matches = []
        # dup() shares directory offsets. Open an independent description so
        # repeated collision checks cannot accidentally begin at end-of-directory.
        scan_fd = os.open(".", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC, dir_fd=descriptor)
        try:
            with os.scandir(scan_fd) as entries:
                for index, entry in enumerate(entries):
                    if index >= 100_000:
                        raise FileError("DIRECTORY_LIMIT")
                    if storage_key(entry.name) == storage_key(requested):
                        matches.append(entry.name)
        finally:
            os.close(scan_fd)
        return matches

    @contextmanager
    def reader(self, path, *, links=1):
        try:
            with self.parent(path) as (parent, name):
                descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=parent)
                try:
                    info = os.fstat(descriptor)
                    if not stat.S_ISREG(info.st_mode) or not 1 <= info.st_nlink <= links:
                        raise FileError("UNSAFE_FILE")
                    yield descriptor, info
                    if fingerprint(os.fstat(descriptor)) != fingerprint(info) or fingerprint(
                        os.stat(name, dir_fd=parent, follow_symlinks=False)
                    ) != fingerprint(info):
                        raise FileError("SOURCE_CHANGED")
                finally:
                    os.close(descriptor)
        except OSError:
            raise FileError("FILE_IO") from None

    def read(self, path, *, maximum, checkpoint=lambda: None, links=1, timeout=120):
        if type(timeout) is not int or not 1 <= timeout <= 600:
            raise FileError("INVALID_LIMIT")
        deadline = time.monotonic() + timeout
        with self.reader(path, links=links) as (descriptor, info):
            if not 0 < info.st_size <= maximum:
                raise FileError("LIMIT_EXCEEDED")
            data = bytearray()
            while chunk := os.read(descriptor, CHUNK):
                if time.monotonic() > deadline:
                    raise FileError("READ_TIMEOUT")
                checkpoint()
                data.extend(chunk)
                if len(data) > maximum:
                    raise FileError("LIMIT_EXCEEDED")
            return bytes(data), info


@dataclass(frozen=True)
class Stage:
    path: str
    info: os.stat_result
    sha256: str
    size: int


def _staging(path):
    parts = PurePosixPath(relative_path(path)).parts
    if len(parts) != 3 or parts[0] != ".staging" or not re.fullmatch(r"[0-9a-f]{32}", parts[1]):
        raise FileError("UNSAFE_STAGING")
    if not re.fullmatch(r"attempt-[1-9][0-9]*\.pdf", parts[2]):
        raise FileError("UNSAFE_STAGING")


def discard_stage(root, path, expected_identity):
    """Remove only this caller's unlinked temporary inode, never a final file."""
    _staging(path)
    if not root.writable:
        raise FileError("READ_ONLY_ROOT")
    with root.parent(path) as (parent, name):
        info = os.stat(name, dir_fd=parent, follow_symlinks=False)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or identity(info) != expected_identity:
            raise FileError("STAGING_CHANGED")
        os.unlink(name, dir_fd=parent)
        os.fsync(parent)


def stage_copy(
    source, source_path, destination, staged_path, *, sha256, size, processor, checkpoint=lambda: None, timeout=120
):
    """Independent bounded copy; input is opened read-only even for canonical moves."""
    _staging(staged_path)
    if not destination.writable:
        raise FileError("READ_ONLY_ROOT")
    if not isinstance(sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", sha256):
        raise FileError("INVALID_IDENTITY")
    if type(size) is not int or not 0 < size <= processor.limits.max_bytes:
        raise FileError("LIMIT_EXCEEDED")
    if type(timeout) is not int or not 1 <= timeout <= 600:
        raise FileError("INVALID_LIMIT")
    deadline = time.monotonic() + timeout

    def guard():
        if time.monotonic() > deadline:
            raise FileError("COPY_TIMEOUT")
        checkpoint()

    created_identity = None
    try:
        with source.reader(source_path) as (input_fd, original):
            if original.st_size != size:
                raise FileError("SOURCE_CHANGED")
            with destination.parent(staged_path, create=True) as (parent, name):
                output_fd = os.open(
                    name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=parent
                )
                created_identity = identity(os.fstat(output_fd))
                try:
                    digest, total = hashlib.sha256(), 0
                    while chunk := os.read(input_fd, CHUNK):
                        guard()
                        total += len(chunk)
                        if total > size:
                            raise FileError("SOURCE_CHANGED")
                        digest.update(chunk)
                        remaining = memoryview(chunk)
                        while remaining:
                            count = os.write(output_fd, remaining)
                            if count <= 0:
                                raise FileError("FILE_IO")
                            remaining = remaining[count:]
                    if total != size or digest.hexdigest() != sha256:
                        raise FileError("SOURCE_CHANGED")
                    os.fchmod(output_fd, 0o440)
                    os.fsync(output_fd)
                finally:
                    os.close(output_fd)
                os.fsync(parent)
            copied, info = destination.read(staged_path, maximum=size, checkpoint=guard)
            if len(copied) != size or hashlib.sha256(copied).hexdigest() != sha256:
                raise FileError("COPY_MISMATCH")
            inspected = processor.inspect(copied)
            guard()
            if inspected.sha256 != sha256:
                raise FileError("COPY_MISMATCH")
        return Stage(staged_path, info, sha256, size)
    except BaseException as error:
        if created_identity is not None:
            # Retain ambiguous temporary files; never guess which inode to remove.
            with suppress(OSError, FileError):
                discard_stage(destination, staged_path, created_identity)
        if isinstance(error, OSError):
            raise FileError("FILE_IO") from None
        raise


def publish(root, stage, target_path):
    """Short no-clobber effect. Retain the stage until durable metadata acknowledges it."""
    _staging(stage.path)
    if not root.writable or storage_key(PurePosixPath(relative_path(target_path)).parts[0]) == ".staging":
        raise FileError("UNSAFE_DESTINATION")
    try:
        if root.directory_spelling(target_path) != target_path or root.collides(target_path):
            raise FileError("DESTINATION_EXISTS")
        with (
            root.parent(stage.path) as (source_parent, source_name),
            root.parent(target_path) as (target_parent, target_name),
        ):
            current = os.stat(source_name, dir_fd=source_parent, follow_symlinks=False)
            if (
                not stat.S_ISREG(current.st_mode)
                or current.st_nlink != 1
                or fingerprint(current) != fingerprint(stage.info)
            ):
                raise FileError("STAGING_CHANGED")
            os.link(source_name, target_name, src_dir_fd=source_parent, dst_dir_fd=target_parent, follow_symlinks=False)
            final = os.stat(target_name, dir_fd=target_parent, follow_symlinks=False)
            if not stat.S_ISREG(final.st_mode) or identity(final) != identity(stage.info):
                raise FileError("PUBLICATION_CONFLICT")
            if root._matching_names(target_parent, target_name) != [target_name]:
                raise FileError("PUBLICATION_CONFLICT")
            os.fsync(target_parent)
    except FileExistsError:
        raise FileError("DESTINATION_EXISTS") from None
    except OSError:
        raise FileError("FILE_IO") from None


def verify_published(
    root, target_path, *, sha256, size, staged_path=None, processor=None, checkpoint=lambda: None, durable=False
):
    """Pending effects require both the expected bytes and the retained stage inode."""
    data, final = root.read(target_path, maximum=size, checkpoint=checkpoint, links=2 if staged_path else 1)
    if len(data) != size or hashlib.sha256(data).hexdigest() != sha256:
        raise FileError("COPY_MISMATCH")
    if staged_path is not None:
        _staging(staged_path)
        staged = root.metadata(staged_path)
        if not stat.S_ISREG(staged.st_mode) or identity(staged) != identity(final) or final.st_nlink != 2:
            raise FileError("PUBLICATION_CONFLICT")
    if processor is not None:
        processor.inspect(data)
    with root.parent(target_path) as (parent, name):
        if root._matching_names(parent, name) != [name]:
            raise FileError("PUBLICATION_CONFLICT")
        if durable:
            if not root.writable:
                raise FileError("READ_ONLY_ROOT")
            with root.reader(target_path, links=2 if staged_path else 1) as (descriptor, checked):
                if fingerprint(checked) != fingerprint(final):
                    raise FileError("SOURCE_CHANGED")
                os.fsync(descriptor)
                os.fsync(parent)
            if staged_path:
                with root.parent(staged_path) as (stage_parent, _stage_name):
                    os.fsync(stage_parent)
    return data, final


def release_stage(root, staged_path, target_path):
    """Only after APPLIED metadata: detach the known stage, retain the final copy."""
    _staging(staged_path)
    if not root.writable:
        raise FileError("READ_ONLY_ROOT")
    try:
        with root.parent(staged_path) as (parent, name):
            staged = os.stat(name, dir_fd=parent, follow_symlinks=False)
            final = root.metadata(target_path)
            if not stat.S_ISREG(staged.st_mode) or identity(staged) != identity(final) or staged.st_nlink != 2:
                raise FileError("PUBLICATION_CONFLICT")
            os.unlink(name, dir_fd=parent)
            os.fsync(parent)
    except FileNotFoundError:
        return
