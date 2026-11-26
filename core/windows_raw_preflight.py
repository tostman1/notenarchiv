"""Bounded read-only RAW evidence aggregation; never isolation certification.

Caller owns an explicitly security-inspectable root context. Paths/SIDs are private
temporary comparison inputs, not report fields. ACL snapshots cannot establish
stable provisioning, descendant-process/thread policy or persistent enforcement.
No recursive bulk pinning: single-entry contexts and bounded directory baselines.
"""

import stat
import time
from dataclasses import dataclass, field

from core import files, inventory
from core import windows_access_security as access
from core.files_windows import WindowsSourceRoot, component


@dataclass(frozen=True)
class PreflightReport:
    complete: bool
    entries_checked: int
    directories_checked: int
    rejections: tuple[str, ...]
    raw_isolation_certified: bool = field(default=False, init=False)
    writable_publication: bool = field(default=False, init=False)


class _Stop(Exception):
    def __init__(self, code):
        self.code = code


def inspect_raw(
    root, expected_user_sid, *, maximum=inventory.MAX_ENTRIES, max_depth=64, timeout=120, checkpoint=lambda: None
):
    """Aggregate root/parent/descendant evidence without retaining private details.

    Cancellation yields an incomplete report; process termination is not swallowed.
    Completeness describes the bounded inventory, not an atomic ACL snapshot.
    """
    if type(expected_user_sid) is not bytes or not 8 <= len(expected_user_sid) <= 68:
        raise files.FileError("INVALID_IDENTITY")
    if (
        type(maximum) is not int
        or not 1 <= maximum <= inventory.MAX_ENTRIES
        or type(max_depth) is not int
        or not 1 <= max_depth <= 64
        or type(timeout) is not int
        or not 1 <= timeout <= 600
    ):
        raise files.FileError("INVALID_LIMIT")
    if not isinstance(root, WindowsSourceRoot) or not root.inspect_security or root._stack is None:
        return PreflightReport(False, 0, 0, ("SECURITY_MODE_REQUIRED",))
    deadline = time.monotonic() + timeout
    rejections, checked, directories = set(), 0, 0
    baselines, pending, seen = [], [], set()

    def guard():
        try:
            checkpoint()
        except Exception:
            raise _Stop("CANCELLED") from None
        if time.monotonic() > deadline:
            raise _Stop("TIME_LIMIT")

    def record(evidence, *, parent=False):
        if evidence.user_sid != expected_user_sid:
            rejections.add("IDENTITY_MISMATCH")
        if not parent and evidence.owner_sid == evidence.user_sid:
            rejections.add("RAW_OWNED_BY_APPLICATION")
        if evidence.dangerous_privileges_present:
            rejections.add("DANGEROUS_TOKEN")
        if evidence.administrative_token:
            rejections.add("ADMINISTRATIVE_TOKEN")
        if parent:
            if evidence.granted_access & (0x40 | 0x40000 | 0x80000):
                rejections.add("PARENT_MUTATION_ACCESS")
        elif evidence.mutation_access:
            rejections.add("RAW_MUTATION_ACCESS")

    def matches(before, after):
        if files.fingerprint(before) != files.fingerprint(after) or before.st_nlink != after.st_nlink:
            raise _Stop("INVENTORY_CHANGED")

    try:
        guard()
        root_before = root.root_metadata()
        record(access.root_access_evidence(root))
        matches(root_before, root.root_metadata())
        checked = 1
        try:
            record(access.parent_access_evidence(root), parent=True)
        except files.FileError as error:
            if error.code == "UNSAFE_ROOT":
                raise _Stop("MISSING_PARENT") from None
            raise
        pending.append(("", root_before, 0))
        while pending:
            guard()
            path, expected, depth = pending.pop()
            with root.directory_entries(path) as (before, entries):
                matches(expected, before)
                identifier = files.identity(before)
                if identifier in seen:
                    raise _Stop("INVENTORY_CHANGED")
                seen.add(identifier)
                directories += 1
                for name, info in entries:
                    guard()
                    if checked >= maximum:
                        raise _Stop("ENTRY_LIMIT")
                    component(name)
                    child = f"{path}/{name}" if path else name
                    if depth + 1 > max_depth:
                        raise _Stop("DEPTH_LIMIT")
                    directory = stat.S_ISDIR(info.st_mode)
                    if not directory and (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1):
                        raise _Stop("UNSAFE_ENTRY")
                    with root.security_entry(child) as (handle, pinned):
                        matches(info, pinned)
                        record(access._handle_access_evidence(handle, directory=directory))
                    matches(info, root.metadata(child))
                    checked += 1
                    if directory:
                        pending.append((child, info, depth + 1))
            matches(before, root.root_metadata() if not path else root.metadata(path))
            baselines.append((path, before))
        # Recheck directories after all their descendants, including earlier siblings.
        for path, before in baselines:
            guard()
            matches(before, root.root_metadata() if not path else root.metadata(path))
    except _Stop as error:
        rejections.add(error.code)
        return PreflightReport(False, checked, directories, tuple(sorted(rejections)))
    except (files.FileError, OSError, ValueError) as error:
        code = getattr(error, "code", "")
        if code == "SOURCE_CHANGED" or isinstance(error, FileNotFoundError):
            rejections.add("INVENTORY_CHANGED")
        elif code in {"UNSAFE_PATH", "UNSAFE_FILE"}:
            rejections.add("UNSAFE_ENTRY")
        else:
            rejections.add("SECURITY_QUERY_FAILED")
        return PreflightReport(False, checked, directories, tuple(sorted(rejections)))
    return PreflightReport(True, checked, directories, tuple(sorted(rejections)))
