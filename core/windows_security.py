"""Read-only current-process token evidence, not RAW isolation certification.

No root security descriptors, effective file access, parent delete-child exposure,
thread impersonation or descendant tokens are inspected here. A dedicated identity
must later be matched to configured identity and RAW ownership/ACL evidence.
Neither a restricted nor a non-elevated token alone enables Windows publication.
SID bytes are private comparison inputs and deliberately excluded from repr.
"""

import ctypes as c
import os
from dataclasses import dataclass, field
from functools import lru_cache
from types import SimpleNamespace

from core.files import FileError

DWORD = c.c_uint32
MAX_TOKEN_BYTES = 1024 * 1024
DANGEROUS_PRIVILEGES = frozenset(
    {
        "SeBackupPrivilege",
        "SeRestorePrivilege",
        "SeTakeOwnershipPrivilege",
        "SeDebugPrivilege",
        "SeImpersonatePrivilege",
        "SeAssignPrimaryTokenPrivilege",
    }
)
# Disabled privileges still present in a token may be enabled by its process.
# Debug/impersonation/assign-primary-token can escape the intended identity boundary.


class SidAttributes(c.Structure):
    _fields_ = [("sid", c.c_void_p), ("attributes", DWORD)]


class Luid(c.Structure):
    _fields_ = [("low", DWORD), ("high", c.c_int32)]


class Privilege(c.Structure):
    _fields_ = [("luid", Luid), ("attributes", DWORD)]


@dataclass(frozen=True)
class TokenEvidence:
    user_sid: bytes = field(repr=False)
    owner_sid: bytes = field(repr=False)
    privileges: tuple[tuple[str, bool], ...]
    elevated: bool
    elevation_type: int
    restricted: bool
    administrator_enabled: bool


@dataclass(frozen=True)
class Capabilities:
    token_policy_rejections: tuple[str, ...]
    raw_isolation_certified: bool = field(default=False, init=False)
    writable_publication: bool = field(default=False, init=False)


def capabilities(evidence):
    """Return explicitly uncertified capabilities even for acceptable token evidence."""
    reasons = []
    if evidence.elevated or evidence.elevation_type == 2 or evidence.administrator_enabled:
        reasons.append("ADMINISTRATIVE_TOKEN")
    if any(name in DANGEROUS_PRIVILEGES for name, _ in evidence.privileges):
        reasons.append("DANGEROUS_PRIVILEGE_PRESENT")
    return Capabilities(tuple(reasons))


@lru_cache(maxsize=1)
def _api():
    if os.name != "nt":
        raise FileError("UNSUPPORTED_SECURITY_API")
    kernel = c.WinDLL("kernel32", use_last_error=True)
    security = c.WinDLL("advapi32", use_last_error=True)
    declarations = {
        "GetCurrentProcess": (kernel, [], c.c_void_p),
        "CloseHandle": (kernel, [c.c_void_p], c.c_int),
        "GetHandleInformation": (kernel, [c.c_void_p, c.POINTER(DWORD)], c.c_int),
        "OpenProcessToken": (security, [c.c_void_p, DWORD, c.POINTER(c.c_void_p)], c.c_int),
        "GetTokenInformation": (security, [c.c_void_p, c.c_int, c.c_void_p, DWORD, c.POINTER(DWORD)], c.c_int),
        "LookupPrivilegeNameW": (security, [c.c_wchar_p, c.POINTER(Luid), c.c_wchar_p, c.POINTER(DWORD)], c.c_int),
        "IsTokenRestricted": (security, [c.c_void_p], c.c_int),
    }
    functions = {}
    for name, (library, args, result) in declarations.items():
        function = getattr(library, name)
        function.argtypes, function.restype = args, result
        functions[name] = function
    return SimpleNamespace(**functions)


def _failure():
    return FileError("SECURITY_QUERY_FAILED")


def _query(api, token, kind):
    needed = DWORD()
    if kind in {18, 20}:  # Fixed DWORD-sized TokenElevationType / TokenElevation.
        buffer = c.create_string_buffer(c.sizeof(DWORD))
        if not api.GetTokenInformation(token, kind, buffer, len(buffer), c.byref(needed)):
            raise _failure()
        if needed.value != len(buffer):
            raise _failure()
        return buffer
    if api.GetTokenInformation(token, kind, None, 0, c.byref(needed)) or c.get_last_error() != 122:
        raise _failure()
    if not 0 < needed.value <= MAX_TOKEN_BYTES:
        raise _failure()
    buffer = c.create_string_buffer(needed.value)
    if not api.GetTokenInformation(token, kind, buffer, len(buffer), c.byref(needed)):
        raise _failure()
    if not 0 < needed.value <= len(buffer):
        raise _failure()
    return buffer


def _sid(buffer, pointer):
    base = c.addressof(buffer)
    if pointer is None or not base <= pointer <= base + len(buffer) - 8:
        raise _failure()
    header = c.string_at(pointer, 8)
    size = 8 + 4 * header[1]
    if header[0] != 1 or header[1] > 15 or pointer + size > base + len(buffer):
        raise _failure()
    return c.string_at(pointer, size)


def _scalar(buffer):
    if len(buffer) < c.sizeof(DWORD):
        raise _failure()
    return DWORD.from_buffer(buffer).value


def _array(buffer, entry):
    class Array(c.Structure):
        _fields_ = [("count", DWORD), ("entries", entry * 1)]

    count = _scalar(buffer)
    offset = Array.entries.offset
    if offset + count * c.sizeof(entry) > len(buffer):
        raise _failure()
    return [entry.from_buffer(buffer, offset + index * c.sizeof(entry)) for index in range(count)]


def _collect(api, token):
    user = _query(api, token, 1)  # TokenUser
    owner = _query(api, token, 4)  # TokenOwner
    if len(user) < c.sizeof(SidAttributes) or len(owner) < c.sizeof(c.c_void_p):
        raise _failure()
    groups = _query(api, token, 2)
    # S-1-5-32-544 (BUILTIN Administrators), binary SID comparison only.
    admin_sid = b"\x01\x02\x00\x00\x00\x00\x00\x05" + (32).to_bytes(4, "little") + (544).to_bytes(4, "little")
    administrator = any(
        _sid(groups, group.sid) == admin_sid and bool(group.attributes & 4) and not group.attributes & 16
        for group in _array(groups, SidAttributes)
    )
    privileges = []
    for item in _array(_query(api, token, 3), Privilege):
        name, length = c.create_unicode_buffer(256), DWORD(256)
        if not api.LookupPrivilegeNameW(None, c.byref(item.luid), name, c.byref(length)):
            raise _failure()
        if not 0 < length.value < len(name):
            raise _failure()
        privileges.append((name.value, bool(item.attributes & 2)))
    elevation_type = _scalar(_query(api, token, 18))
    elevation = _scalar(_query(api, token, 20))
    if elevation_type not in {1, 2, 3} or elevation not in {0, 1}:
        raise _failure()
    return TokenEvidence(
        _sid(user, SidAttributes.from_buffer(user).sid),
        _sid(owner, c.c_void_p.from_buffer(owner).value),
        tuple(sorted(privileges)),
        bool(elevation),
        elevation_type,
        bool(api.IsTokenRestricted(token)),
        administrator,
    )


def current_process_token():
    """Query only the current primary process token with TOKEN_QUERY (0x0008).

    Uses OpenProcessToken/GetTokenInformation/LookupPrivilegeNameW; no token
    duplication, privilege adjustment, ACL modification or inheritable handles.
    """
    if os.name != "nt":
        raise FileError("UNSUPPORTED_SECURITY_API")
    token = c.c_void_p()
    try:
        api = _api()
        if not api.OpenProcessToken(api.GetCurrentProcess(), 0x0008, c.byref(token)):
            raise _failure()
        try:
            flags = DWORD()
            if not api.GetHandleInformation(token, c.byref(flags)) or flags.value & 1:
                raise _failure()
            return _collect(api, token)
        finally:
            if not api.CloseHandle(token):
                raise _failure()
    except FileError:
        raise
    # ctypes buffer decoding and argument conversion can contain private native
    # values in their exception text; sanitize them at the query boundary too.
    except (OSError, AttributeError, ValueError, c.ArgumentError):
        raise _failure() from None
