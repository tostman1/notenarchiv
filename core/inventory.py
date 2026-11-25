"""Bounded descriptor-relative RAW inventories and stable streaming hashes."""

import hashlib
import os
import stat
import time
from pathlib import PurePosixPath

from core import files
from core.paths import relative_path

MAX_ENTRIES = 10_000


def scan(root, selected, *, checkpoint=lambda: None, maximum=MAX_ENTRIES):
    """Snapshot all entries; unsafe entries are reported, never followed.

    Failure to enumerate any directory invalidates the entire inventory: callers
    must not infer missing sources from a partial walk.
    """
    result, pending, seen = [], [relative_path(selected, allow_root=True)], set()
    deadline = time.monotonic() + 120
    while pending:
        checkpoint()
        if time.monotonic() > deadline:
            raise files.FileError("INVENTORY_TIMEOUT")
        path = pending.pop()
        with root.directory_entries(path) as (metadata, entries):
            identity = files.identity(metadata)
            if identity in seen:
                raise files.FileError("DIRECTORY_CONFLICT")
            seen.add(identity)
            result.append({"path": path, "kind": "DIRECTORY"})
            for name, info in entries:
                checkpoint()
                if len(result) + len(pending) >= maximum:
                    raise files.FileError("DIRECTORY_LIMIT")
                child = str(PurePosixPath(path, name))
                relative_path(child)
                if stat.S_ISDIR(info.st_mode):
                    pending.append(child)
                else:
                    result.append(
                        {
                            "path": child,
                            "kind": "FILE" if stat.S_ISREG(info.st_mode) and info.st_nlink == 1 else "UNSAFE",
                            "fingerprint": list(files.fingerprint(info)),
                        }
                    )
    return sorted(result, key=lambda item: item["path"])


def read_hash(root, path, *, maximum, expected=None, retain=True, checkpoint=lambda: None):
    deadline = time.monotonic() + 120
    with root.reader(path) as (descriptor, info):
        if expected is not None and list(files.fingerprint(info)) != expected:
            raise files.FileError("SOURCE_CHANGED")
        if info.st_size > maximum:
            raise files.FileError("LIMIT_EXCEEDED")
        digest, total, data = hashlib.sha256(), 0, bytearray()
        while chunk := os.read(descriptor, files.CHUNK):
            checkpoint()
            if time.monotonic() > deadline:
                raise files.FileError("READ_TIMEOUT")
            total += len(chunk)
            if total > maximum:
                raise files.FileError("LIMIT_EXCEEDED")
            digest.update(chunk)
            if retain:
                data.extend(chunk)
        if total != info.st_size:
            raise files.FileError("SOURCE_CHANGED")
    return digest.hexdigest(), bytes(data), info
