"""Read-only, hash-verified snapshots for the authenticated preview boundary."""

import hashlib
import os
import stat
import time
from contextlib import ExitStack, contextmanager
from pathlib import Path

from core.files import FileError, Root, fingerprint
from core.paths import relative_path


def snapshot(root, path, *, maximum, sha256, size):
    relative_path(path)
    if any(part.startswith(".") for part in path.split("/")):
        raise FileError("UNSAFE_PATH")
    if not 0 < size <= maximum:
        raise FileError("LIMIT_EXCEEDED")
    if os.name == "posix":
        with Root(root) as opened:
            # Publication can temporarily retain a second staging hard link.
            data, _info = opened.read(path, maximum=maximum, links=2, timeout=15)
    elif os.name == "nt":
        data = _windows_snapshot(root, path, maximum)
    else:
        raise FileError("UNSUPPORTED_FILESYSTEM_API")
    if len(data) != size or hashlib.sha256(data).hexdigest() != sha256:
        raise FileError("CONTENT_CHANGED")
    return data


def _windows_snapshot(root, path, maximum):
    with _windows_reader(root, path, maximum) as (stream, info):
        data = stream.read(maximum + 1)
        if len(data) > maximum or fingerprint(os.fstat(stream.fileno())) != fingerprint(info):
            raise FileError("SOURCE_CHANGED")
        return data


@contextmanager
def _windows_reader(root, path, maximum):
    """Validate the actual opened handle, not just a pre-open path resolution."""
    import ctypes
    import msvcrt
    from ctypes import wintypes

    root = Path(root)
    target = root.joinpath(*path.split("/"))
    if not root.is_absolute() or root != root.resolve(strict=True):
        raise FileError("UNSAFE_ROOT")
    for component in (target, *target.parents):
        info = component.lstat()
        if info.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            raise FileError("UNSAFE_PATH")
    flags = os.O_RDONLY | os.O_BINARY | os.O_NOINHERIT
    with os.fdopen(os.open(target, flags), "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= maximum or info.st_nlink > 2:
            raise FileError("UNSAFE_FILE")
        function = ctypes.WinDLL("kernel32", use_last_error=True).GetFinalPathNameByHandleW
        function.argtypes = [wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD]
        function.restype = wintypes.DWORD
        buffer = ctypes.create_unicode_buffer(32768)
        length = function(msvcrt.get_osfhandle(stream.fileno()), buffer, len(buffer), 0)
        if not 0 < length < len(buffer) or Path(buffer.value.removeprefix("\\\\?\\")) != target:
            raise FileError("UNSAFE_PATH")
        yield stream, info
        if fingerprint(os.fstat(stream.fileno())) != fingerprint(info):
            raise FileError("SOURCE_CHANGED")


def copy_snapshot(root, path, target, *, maximum, sha256, size, checkpoint=lambda: None):
    """Stream verified immutable bytes into private staging, never serve source handles."""
    relative_path(path)
    if any(part.startswith(".") for part in path.split("/")) or not 0 < size <= maximum:
        raise FileError("UNSAFE_PATH")
    with ExitStack() as stack:
        if os.name == "posix":
            opened = stack.enter_context(Root(root))
            descriptor, info = stack.enter_context(opened.reader(path, links=2))
        elif os.name == "nt":
            stream, info = stack.enter_context(_windows_reader(root, path, maximum))
            descriptor = stream.fileno()
        else:
            raise FileError("UNSUPPORTED_FILESYSTEM_API")
        if info.st_size != size:
            raise FileError("CONTENT_CHANGED")
        total, digest = 0, hashlib.sha256()
        deadline = time.monotonic() + 15
        while chunk := os.read(descriptor, 1_048_576):
            checkpoint()
            total += len(chunk)
            if total > size or time.monotonic() > deadline:
                raise FileError("LIMIT_EXCEEDED")
            digest.update(chunk)
            target.write(chunk)
        if total != size or digest.hexdigest() != sha256:
            raise FileError("CONTENT_CHANGED")
