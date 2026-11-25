"""Bounded unchanged PDF/ZIP staging; no PDF transformation or persistent artifact."""

import hashlib
import os
import re
import stat
import tempfile
import time
import zipfile
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path

from core.files import FileError, Root
from core.preview import copy_snapshot

MAX_FILES = 20
MAX_TOTAL = 512 * 1024**2
MAX_FILE = 100 * 1024**2
CHUNK = 1_048_576


@dataclass(frozen=True)
class Input:
    root: Path
    path: str
    sha256: str
    size: int
    filename: str


def scratch_directory(parent):
    """Only below trusted application DATA; never use archive roots as scratch."""
    parent = Path(parent)
    if os.name == "posix":
        with Root(parent, writable=True) as root:
            root.ensure_private_directory("download-scratch")
    elif os.name == "nt":
        if not parent.is_absolute() or parent != parent.resolve(strict=True):
            raise FileError("UNSAFE_ROOT")
        for path in (parent, *parent.parents):
            if path.lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                raise FileError("UNSAFE_ROOT")
        (parent / "download-scratch").mkdir(mode=0o700, exist_ok=True)
        if (parent / "download-scratch").lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            raise FileError("UNSAFE_STAGING")
    else:
        raise FileError("UNSUPPORTED_FILESYSTEM_API")
    return parent / "download-scratch"


def build(inputs, scratch, *, zipped):
    if not 1 <= len(inputs) <= MAX_FILES or sum(item.size for item in inputs) > MAX_TOTAL:
        raise FileError("DOWNLOAD_LIMIT")
    if not zipped and len(inputs) != 1:
        raise FileError("DOWNLOAD_LIMIT")
    if any(not 0 < item.size <= MAX_FILE for item in inputs) or len({item.filename for item in inputs}) != len(inputs):
        raise FileError("DOWNLOAD_LIMIT")
    if any(not re.fullmatch(r"note-[0-9a-f-]{36}\.pdf", item.filename) for item in inputs):
        raise FileError("UNSAFE_DOWNLOAD_NAME")
    owner = ExitStack()
    # Successful callers own the stream until response.close(); lexical `with`
    # would close it before HTTP streaming. ExitStack owns every failure path.
    output = owner.enter_context(tempfile.TemporaryFile(mode="w+b", dir=scratch))  # noqa: SIM115
    deadline = time.monotonic() + 60

    def checkpoint():
        if time.monotonic() > deadline or output.tell() > MAX_TOTAL + CHUNK:
            raise FileError("DOWNLOAD_LIMIT")

    def copy(item, stream):
        copy_snapshot(
            item.root, item.path, stream, maximum=MAX_FILE, sha256=item.sha256, size=item.size, checkpoint=checkpoint
        )

    try:
        if zipped:
            with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED, allowZip64=False) as archive:
                for item in inputs:
                    name = zipfile.ZipInfo(item.filename, date_time=(1980, 1, 1, 0, 0, 0))
                    name.external_attr = 0o600 << 16
                    with archive.open(name, "w") as member:
                        copy(item, member)
        else:
            copy(inputs[0], output)
        output.flush()
        checkpoint()
        output.seek(0)

        def verify(stream, item):
            digest, size = hashlib.sha256(), 0
            while chunk := stream.read(CHUNK):
                checkpoint()
                size += len(chunk)
                digest.update(chunk)
            if (size, digest.hexdigest()) != (item.size, item.sha256):
                raise FileError("DOWNLOAD_INTEGRITY")

        if zipped:
            with zipfile.ZipFile(output) as archive:
                if archive.namelist() != [item.filename for item in inputs]:
                    raise FileError("DOWNLOAD_INTEGRITY")
                for item in inputs:
                    if archive.getinfo(item.filename).file_size != item.size:
                        raise FileError("DOWNLOAD_INTEGRITY")
                    with archive.open(item.filename) as stream:
                        verify(stream, item)
        else:
            verify(output, inputs[0])
        output.seek(0)
        owner.pop_all()  # Ownership explicitly transfers to the response stream.
        return output
    except BaseException:
        owner.close()
        raise
