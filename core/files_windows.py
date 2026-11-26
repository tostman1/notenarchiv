"""Read-only local NTFS source access; no publication or ACL modification.

Directory handles deny delete sharing while their paths are used. Every opened
component rejects reparses; source streams additionally deny write sharing.
All fingerprints use native handle metadata, never CRT timestamp precision.
"""

import ctypes
import errno
import hashlib
import os
import re
import stat
import time
from contextlib import ExitStack, contextmanager
from ctypes import wintypes as w
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path, PurePosixPath

from core.files import CHUNK, FileError, fingerprint
from core.naming import RESERVED
from core.paths import relative_path

REPARSE = 0x400
FILETIME_EPOCH = 116444736000000000


def _directory_names(directory):
    """Bounded-memory, order-independent inventory independent of NTFS timestamps."""
    count = total = 0
    with os.scandir(directory) as entries:
        for entry in entries:
            count += 1
            if count > 100_000:
                raise FileError("LIMIT_EXCEEDED")
            total = (total + int.from_bytes(hashlib.sha256(os.fsencode(entry.name)).digest())) % (1 << 256)
    return count, total


class BasicInfo(ctypes.Structure):
    _fields_ = [(name, ctypes.c_longlong) for name in ("created", "accessed", "written", "changed")] + [
        ("attributes", w.DWORD)
    ]


class StandardInfo(ctypes.Structure):
    _fields_ = [
        ("allocation", ctypes.c_longlong),
        ("size", ctypes.c_longlong),
        ("links", w.DWORD),
        ("pending", ctypes.c_ubyte),
        ("directory", ctypes.c_ubyte),
    ]


class IdInfo(ctypes.Structure):
    _fields_ = [("volume", ctypes.c_ulonglong), ("identifier", ctypes.c_ubyte * 16)]


@dataclass(frozen=True)
class Metadata:
    st_dev: int
    st_ino: int
    st_mode: int
    st_nlink: int
    st_size: int
    st_mtime_ns: int
    st_ctime_ns: int


@lru_cache(maxsize=1)
def kernel():
    if os.name != "nt":
        raise FileError("UNSUPPORTED_FILESYSTEM_API")
    api = ctypes.WinDLL("kernel32", use_last_error=True)
    declarations = {
        "CreateFileW": ([w.LPCWSTR, w.DWORD, w.DWORD, w.LPVOID, w.DWORD, w.DWORD, w.HANDLE], w.HANDLE),
        "CloseHandle": ([w.HANDLE], w.BOOL),
        "GetFileInformationByHandleEx": ([w.HANDLE, ctypes.c_int, w.LPVOID, w.DWORD], w.BOOL),
        "GetFinalPathNameByHandleW": ([w.HANDLE, w.LPWSTR, w.DWORD, w.DWORD], w.DWORD),
        "GetVolumeInformationByHandleW": (
            [w.HANDLE, w.LPWSTR, w.DWORD, w.LPDWORD, w.LPDWORD, w.LPDWORD, w.LPWSTR, w.DWORD],
            w.BOOL,
        ),
        "GetDriveTypeW": ([w.LPCWSTR], w.UINT),
    }
    for name, (arguments, result) in declarations.items():
        function = getattr(api, name)
        function.argtypes, function.restype = arguments, result
    return api


def component(name):
    if (
        not name
        or name.endswith((".", " "))
        or RESERVED.match(name)
        or any(char in '<>:"/\\|?*' or ord(char) < 32 for char in name)
    ):
        raise FileError("UNSAFE_PATH")


def information(handle):
    values = (BasicInfo(), StandardInfo(), IdInfo())
    for kind, value in zip((0, 1, 18), values, strict=True):
        if not kernel().GetFileInformationByHandleEx(handle, kind, ctypes.byref(value), ctypes.sizeof(value)):
            raise FileError("FILE_IO")
    basic, standard, identifier = values
    if standard.pending:
        raise FileError("SOURCE_CHANGED")
    mode = stat.S_IFLNK if basic.attributes & REPARSE else stat.S_IFDIR if standard.directory else stat.S_IFREG
    return Metadata(
        identifier.volume,
        int.from_bytes(bytes(identifier.identifier), "little"),
        mode | 0o400,
        standard.links,
        standard.size,
        (basic.written - FILETIME_EPOCH) * 100,
        (basic.changed - FILETIME_EPOCH) * 100,
    )


@contextmanager
def opened(path, *, stream=False, inspect_security=False, pin_read=False):
    # READ_DATA/LIST_DIRECTORY participates in sharing checks; attributes alone
    # do not reliably pin a directory against rename. Never request write access.
    handle = kernel().CreateFileW(
        str(path),
        0x80000000 if stream else 0x81 | (0x20000 if inspect_security else 0),
        1 if stream or pin_read else 3,
        None,
        3,
        0x02200000,
        None,
    )
    if handle == w.HANDLE(-1).value:
        error = ctypes.get_last_error()
        if error in {2, 3}:
            raise FileNotFoundError(errno.ENOENT, "Source entry missing")
        raise OSError(error, "Native source access failed")
    descriptor = None
    try:
        final = ctypes.create_unicode_buffer(32768)
        length = kernel().GetFinalPathNameByHandleW(handle, final, len(final), 0)
        if not 0 < length < len(final) or final.value.casefold() != ("\\\\?\\" + str(path)).casefold():
            raise FileError("UNSAFE_PATH")
        if stream:
            import msvcrt

            descriptor = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
        yield handle, descriptor
    finally:
        if descriptor is not None:
            os.close(descriptor)
        else:
            kernel().CloseHandle(handle)


class WindowsSourceRoot:
    """Narrow read-only source contract on local fixed NTFS volumes.

    UNC, device/short-name aliases, reparses and writable operations remain
    unavailable. No claim of a Windows publication backend or RAW ACL enforcement.
    """

    writable = False

    def __init__(self, path, *, inspect_security=False):
        if type(inspect_security) is not bool:
            raise FileError("UNSAFE_ROOT")
        self.path = Path(path)
        # Explicit initial pin access only; no later pathname reopen or escalation.
        self.inspect_security = inspect_security
        self._stack, self._handle = None, None
        self._parent_handle = None

    def __enter__(self):
        if self._stack is not None:
            raise FileError("UNSAFE_ROOT")
        if (
            os.name != "nt"
            or not self.path.is_absolute()
            or ".." in self.path.parts
            or not re.fullmatch(r"[A-Za-z]:", self.path.drive)
            or len(self.path.parts) > 64
        ):
            raise FileError("UNSAFE_ROOT")
        for name in self.path.parts[1:]:
            component(name)
        stack = ExitStack()
        try:
            current = Path(self.path.anchor)
            if kernel().GetDriveTypeW(str(current)) != 3:
                raise FileError("UNSUPPORTED_FILESYSTEM_API")
            handle, parent_handle = None, None
            for name in (None, *self.path.parts[1:]):
                if name is not None:
                    current /= name
                parent_handle = handle
                handle, _ = stack.enter_context(opened(current, inspect_security=self.inspect_security))
                if not stat.S_ISDIR(information(handle).st_mode):
                    raise FileError("UNSAFE_ROOT")
            filesystem = ctypes.create_unicode_buffer(32)
            if not kernel().GetVolumeInformationByHandleW(
                handle, None, 0, None, None, None, filesystem, len(filesystem)
            ):
                raise FileError("FILE_IO")
            if filesystem.value != "NTFS":
                raise FileError("UNSUPPORTED_FILESYSTEM_API")
            self._stack, self._handle = stack, handle
            self._parent_handle = parent_handle
        except BaseException as error:
            stack.close()
            if isinstance(error, OSError):
                raise FileError("UNSAFE_ROOT") from None
            raise
        return self

    def __exit__(self, *exception):
        if self._stack is not None:
            self._stack.close()
            self._stack, self._handle = None, None
            self._parent_handle = None

    def root_metadata(self):
        if self._handle is None:
            raise FileError("UNSAFE_ROOT")
        return information(self._handle)

    @contextmanager
    def _directory(self, reference, *, inspect_security=False):
        reference = relative_path(reference, allow_root=True)
        if self._stack is None:
            raise FileError("UNSAFE_ROOT")
        parts = PurePosixPath(reference).parts
        if len(parts) > 64:
            raise FileError("UNSAFE_PATH")
        current, handle = self.path, self._handle
        with ExitStack() as stack:
            for name in parts:
                component(name)
                current /= name
                handle, _ = stack.enter_context(opened(current, inspect_security=inspect_security))
                if not stat.S_ISDIR(information(handle).st_mode):
                    raise FileError("UNSAFE_PATH")
            yield current, handle

    @contextmanager
    def security_entry(self, reference):
        """Borrow one no-reparse entry with read-control for this context only."""
        if not self.inspect_security or self._stack is None:
            raise FileError("UNSAFE_ROOT")
        parts = PurePosixPath(relative_path(reference)).parts
        component(parts[-1])
        parent_reference = str(PurePosixPath(*parts[:-1])) if len(parts) > 1 else ""
        try:
            with (
                self._directory(parent_reference, inspect_security=True) as (parent, _),
                opened(parent / parts[-1], inspect_security=True, pin_read=True) as (handle, _),
            ):
                before = information(handle)
                if not stat.S_ISDIR(before.st_mode) and (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1):
                    raise FileError("UNSAFE_FILE")
                yield handle, before
                after = information(handle)
                if fingerprint(after) != fingerprint(before) or after.st_nlink != before.st_nlink:
                    raise FileError("SOURCE_CHANGED")
        except OSError:
            raise FileError("FILE_IO") from None

    @contextmanager
    def security_parent(self):
        """Borrow the immediate parent pin retained at initial root traversal."""
        if not self.inspect_security or self._stack is None or self._parent_handle is None:
            raise FileError("UNSAFE_ROOT")
        before = information(self._parent_handle)
        if not stat.S_ISDIR(before.st_mode):
            raise FileError("UNSAFE_ROOT")
        yield self._parent_handle, before
        if fingerprint(information(self._parent_handle)) != fingerprint(before):
            raise FileError("SOURCE_CHANGED")

    @contextmanager
    def _leaf(self, reference, *, stream=False):
        parts = PurePosixPath(relative_path(reference)).parts
        component(parts[-1])
        with (
            self._directory(str(PurePosixPath(*parts[:-1])) if len(parts) > 1 else "") as (parent, _),
            opened(parent / parts[-1], stream=stream) as item,
        ):
            yield item

    def metadata(self, path):
        try:
            with self._leaf(path) as (handle, _):
                return information(handle)
        except FileNotFoundError:
            raise
        except OSError:
            raise FileError("FILE_IO") from None

    def exists(self, path):
        try:
            self.metadata(path)
            return True
        except FileNotFoundError:
            return False

    @contextmanager
    def directory_entries(self, path):
        path = relative_path(path, allow_root=True)
        try:
            with self._directory(path) as (directory, handle):
                before = information(handle)
                names_before = _directory_names(directory)
                with os.scandir(directory) as entries:
                    yield (
                        before,
                        (
                            (entry.name, self.metadata(f"{path}/{entry.name}" if path else entry.name))
                            for entry in entries
                        ),
                    )
                if (
                    fingerprint(information(handle)) != fingerprint(before)
                    or _directory_names(directory) != names_before
                ):
                    raise FileError("SOURCE_CHANGED")
        except OSError:
            raise FileError("FILE_IO") from None

    @contextmanager
    def reader(self, path, *, links=1):
        try:
            with self._leaf(path, stream=True) as (handle, descriptor):
                info = information(handle)
                if not stat.S_ISREG(info.st_mode) or not 1 <= info.st_nlink <= links:
                    raise FileError("UNSAFE_FILE")
                yield descriptor, info
                after = information(handle)
                if fingerprint(after) != fingerprint(info) or after.st_nlink != info.st_nlink:
                    raise FileError("SOURCE_CHANGED")
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
            if len(data) != info.st_size:
                raise FileError("SOURCE_CHANGED")
            return bytes(data), info
