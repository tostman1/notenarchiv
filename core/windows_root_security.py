"""Read-only descriptor evidence for an already pinned Windows source root.

GetSecurityInfo requires READ_CONTROL on the existing handle. Source-reader pins
currently lack that right: fail closed, never reopen a pathname or adjust access.
Owner/ACL snapshots are not effective-access checks or stable ACL enforcement.
Descendants, parent delete-child rights and process identities remain unchecked.
No evidence here certifies RAW isolation or enables writable publication.
"""

import ctypes as c
import os
import stat
from dataclasses import dataclass, field
from functools import lru_cache
from types import SimpleNamespace

from core.files import FileError
from core.files_windows import WindowsSourceRoot

DWORD = c.c_uint32
MAX_DESCRIPTOR_BYTES = 1024 * 1024
MAX_ACES = 4096


class AclSize(c.Structure):
    _fields_ = [("count", DWORD), ("used", DWORD), ("free", DWORD)]


@dataclass(frozen=True)
class RootSecurityEvidence:
    owner_sid: bytes = field(repr=False)
    dacl_present: bool
    dacl_null: bool
    dacl_protected: bool
    ace_count: int
    raw_isolation_certified: bool = field(default=False, init=False)
    writable_publication: bool = field(default=False, init=False)


def _failure():
    return FileError("SECURITY_QUERY_FAILED")


@lru_cache(maxsize=1)
def _api():
    if os.name != "nt":
        raise FileError("UNSUPPORTED_SECURITY_API")
    kernel, security = c.WinDLL("kernel32", use_last_error=True), c.WinDLL("advapi32", use_last_error=True)
    declarations = {
        "LocalFree": (kernel, [c.c_void_p], c.c_void_p),
        "GetSecurityInfo": (security, [c.c_void_p, c.c_int, DWORD] + [c.POINTER(c.c_void_p)] * 5, DWORD),
        "IsValidSecurityDescriptor": (security, [c.c_void_p], c.c_int),
        "GetSecurityDescriptorLength": (security, [c.c_void_p], DWORD),
        "GetSecurityDescriptorControl": (security, [c.c_void_p, c.POINTER(c.c_uint16), c.POINTER(DWORD)], c.c_int),
        "GetSecurityDescriptorOwner": (security, [c.c_void_p, c.POINTER(c.c_void_p), c.POINTER(c.c_int)], c.c_int),
        "GetSecurityDescriptorDacl": (
            security,
            [c.c_void_p, c.POINTER(c.c_int), c.POINTER(c.c_void_p), c.POINTER(c.c_int)],
            c.c_int,
        ),
        "IsValidSid": (security, [c.c_void_p], c.c_int),
        "GetLengthSid": (security, [c.c_void_p], DWORD),
        "CopySid": (security, [DWORD, c.c_void_p, c.c_void_p], c.c_int),
        "IsValidAcl": (security, [c.c_void_p], c.c_int),
        "GetAclInformation": (security, [c.c_void_p, c.c_void_p, DWORD, c.c_int], c.c_int),
    }
    functions = {}
    for name, (library, args, result) in declarations.items():
        function = getattr(library, name)
        function.argtypes, function.restype = args, result
        functions[name] = function
    return SimpleNamespace(**functions)


def _inside(base, length, pointer, size):
    return pointer is not None and size <= length and base <= pointer <= base + length - size


def _collect(api, descriptor):
    if not api.IsValidSecurityDescriptor(descriptor):
        raise _failure()
    length = api.GetSecurityDescriptorLength(descriptor)
    control, revision = c.c_uint16(), DWORD()
    if not 20 <= length <= MAX_DESCRIPTOR_BYTES or not api.GetSecurityDescriptorControl(
        descriptor, c.byref(control), c.byref(revision)
    ):
        raise _failure()
    # Bound embedded pointers only for a self-relative descriptor (SE_SELF_RELATIVE).
    if not control.value & 0x8000 or revision.value != 1:
        raise _failure()
    owner, defaulted = c.c_void_p(), c.c_int()
    if not api.GetSecurityDescriptorOwner(descriptor, c.byref(owner), c.byref(defaulted)):
        raise _failure()
    base = descriptor.value
    if not _inside(base, length, owner.value, 8) or not api.IsValidSid(owner):
        raise _failure()
    sid_length = api.GetLengthSid(owner)
    if not 8 <= sid_length <= 68 or not _inside(base, length, owner.value, sid_length):
        raise _failure()
    sid = c.create_string_buffer(sid_length)
    if not api.CopySid(sid_length, sid, owner):
        raise _failure()
    present, dacl = c.c_int(), c.c_void_p()
    if not api.GetSecurityDescriptorDacl(descriptor, c.byref(present), c.byref(dacl), c.byref(defaulted)):
        raise _failure()
    count = 0
    if present.value and dacl.value:
        if not _inside(base, length, dacl.value, 8) or not api.IsValidAcl(dacl):
            raise _failure()
        size = AclSize()
        if not api.GetAclInformation(dacl, c.byref(size), c.sizeof(size), 2):  # AclSizeInformation
            raise _failure()
        if size.count > MAX_ACES or size.used < 8 or not _inside(base, length, dacl.value, size.used + size.free):
            raise _failure()
        count = size.count
    return RootSecurityEvidence(
        sid.raw, bool(present.value), bool(present.value and not dacl.value), bool(control.value & 0x1000), count
    )


def root_security_evidence(root):
    """Query the borrowed pinned handle; release only GetSecurityInfo's allocation."""
    if os.name != "nt":
        raise FileError("UNSUPPORTED_SECURITY_API")
    if not isinstance(root, WindowsSourceRoot) or root._stack is None or root._handle is None:
        raise FileError("UNSAFE_ROOT")
    descriptor = c.c_void_p()
    try:
        if not stat.S_ISDIR(root.root_metadata().st_mode):
            raise FileError("UNSAFE_ROOT")
        api = _api()
        try:
            # SE_FILE_OBJECT=1; OWNER_SECURITY_INFORMATION|DACL_SECURITY_INFORMATION=5.
            if api.GetSecurityInfo(root._handle, 1, 5, None, None, None, None, c.byref(descriptor)) != 0:
                raise _failure()
            if descriptor.value is None:
                raise _failure()
            return _collect(api, descriptor)
        finally:
            if descriptor.value is not None and api.LocalFree(descriptor):
                raise _failure()
    except FileError:
        raise
    except (OSError, AttributeError, ValueError, c.ArgumentError):
        raise _failure() from None
