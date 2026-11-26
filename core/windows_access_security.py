"""Current-primary-token AccessCheck evidence for a borrowed pinned RAW root.

This is an ACL snapshot, not an open/write attempt or isolation certification.
Root ownership and root mutation rights do not cover descendants or parent-entry
deletion. Configured identity, thread impersonation, all process roles and dangerous
privilege policy still require separate enforcement. No pathname opens or ACL writes.
"""

import ctypes as c
import os
import stat
from contextlib import ExitStack
from dataclasses import dataclass, field
from functools import lru_cache
from types import SimpleNamespace

from core import windows_root_security as descriptors
from core import windows_security as tokens
from core.files import FileError
from core.files_windows import WindowsSourceRoot

DWORD = c.c_uint32
MAX_PRIVILEGE_BYTES = 65536
FILE_MUTATION_MASK = 0x000D0116  # WRITE/APPEND/EA/ATTRIBUTES, DELETE, WRITE_DAC, WRITE_OWNER.
DIRECTORY_MUTATION_MASK = FILE_MUTATION_MASK | 0x40  # FILE_DELETE_CHILD; 2/4 also add file/subdirectory.


class GenericMapping(c.Structure):
    _fields_ = [(name, DWORD) for name in ("read", "write", "execute", "all")]


@dataclass(frozen=True)
class AccessEvidence:
    owner_sid: bytes = field(repr=False)
    user_sid: bytes = field(repr=False)
    owner_is_process_user: bool
    granted_access: int
    mutation_access: int
    access_allowed: bool
    directory: bool
    dangerous_privileges_present: bool
    administrative_token: bool
    raw_isolation_certified: bool = field(default=False, init=False)
    writable_publication: bool = field(default=False, init=False)


def _failure():
    return FileError("SECURITY_QUERY_FAILED")


@lru_cache(maxsize=1)
def _api():
    if os.name != "nt":
        raise FileError("UNSUPPORTED_SECURITY_API")
    security = c.WinDLL("advapi32", use_last_error=True)
    declarations = {
        "DuplicateTokenEx": ([c.c_void_p, DWORD, c.c_void_p, c.c_int, c.c_int, c.POINTER(c.c_void_p)], c.c_int),
        "AccessCheck": (
            [
                c.c_void_p,
                c.c_void_p,
                DWORD,
                c.POINTER(GenericMapping),
                c.c_void_p,
                c.POINTER(DWORD),
                c.POINTER(DWORD),
                c.POINTER(c.c_int),
            ],
            c.c_int,
        ),
    }
    functions = {}
    for name, (args, result) in declarations.items():
        function = getattr(security, name)
        function.argtypes, function.restype = args, result
        functions[name] = function
    return SimpleNamespace(**functions)


def _check(api, descriptor, token):
    mapping = GenericMapping(0x120089, 0x120116, 0x1200A0, 0x1F01FF)
    size = 256
    for _ in range(3):
        privileges = c.create_string_buffer(size)
        required, granted, allowed = DWORD(size), DWORD(), c.c_int()
        if api.AccessCheck(
            descriptor,
            token,
            0x02000000,
            c.byref(mapping),
            privileges,
            c.byref(required),
            c.byref(granted),
            c.byref(allowed),
        ):
            if required.value > size or allowed.value not in {0, 1} or (not allowed.value and granted.value):
                raise _failure()
            return bool(allowed.value), granted.value
        if c.get_last_error() != 122 or not size < required.value <= MAX_PRIVILEGE_BYTES:
            raise _failure()
        size = required.value
    raise _failure()


def _close(api, handle):
    if not api.CloseHandle(handle):
        raise _failure()


def _free(api, descriptor):
    if api.LocalFree(descriptor):
        raise _failure()


def _noninheritable(api, handle):
    flags = DWORD()
    if not api.GetHandleInformation(handle, c.byref(flags)) or flags.value & 1:
        raise _failure()


def root_access_evidence(root):
    """Check a pinned directory against a query-only duplicate of the primary token.

    DuplicateTokenEx uses SecurityImpersonation=2, TokenImpersonation=2, but the
    token is never installed on a thread. GetSecurityInfo includes GROUP because
    AccessCheck requires both owner and group. READ_CONTROL is required on root.
    """
    if os.name != "nt":
        raise FileError("UNSUPPORTED_SECURITY_API")
    if not isinstance(root, WindowsSourceRoot) or root._stack is None or root._handle is None:
        raise FileError("UNSAFE_ROOT")
    try:
        if not stat.S_ISDIR(root.root_metadata().st_mode):
            raise FileError("UNSAFE_ROOT")
        api, token_api, descriptor_api = _api(), tokens._api(), descriptors._api()
        with ExitStack() as resources:
            primary = c.c_void_p()
            if not token_api.OpenProcessToken(token_api.GetCurrentProcess(), 0xA, c.byref(primary)):
                raise _failure()  # TOKEN_QUERY | TOKEN_DUPLICATE only.
            resources.callback(_close, token_api, primary)
            _noninheritable(token_api, primary)
            evidence = tokens._collect(token_api, primary)
            duplicate = c.c_void_p()
            if not api.DuplicateTokenEx(primary, 8, None, 2, 2, c.byref(duplicate)):
                raise _failure()
            resources.callback(_close, token_api, duplicate)
            _noninheritable(token_api, duplicate)
            descriptor = c.c_void_p()
            result = descriptor_api.GetSecurityInfo(root._handle, 1, 7, None, None, None, None, c.byref(descriptor))
            if descriptor.value is not None:
                resources.callback(_free, descriptor_api, descriptor)
            if result or descriptor.value is None:
                raise _failure()
            owner = descriptors._collect(descriptor_api, descriptor).owner_sid
            allowed, granted = _check(api, descriptor, duplicate)
            return AccessEvidence(
                owner,
                evidence.user_sid,
                owner == evidence.user_sid,
                granted,
                granted & DIRECTORY_MUTATION_MASK,
                allowed,
                True,
                any(name in tokens.DANGEROUS_PRIVILEGES for name, _ in evidence.privileges),
                evidence.elevated or evidence.elevation_type == 2 or evidence.administrator_enabled,
            )
    except FileError:
        raise
    except (OSError, AttributeError, ValueError, c.ArgumentError):
        raise _failure() from None
