"""Linux mountinfo parsing and mount identity checks without write probes."""

import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


@dataclass(frozen=True)
class Mount:
    target: Path
    device: str
    root: str
    readonly: bool
    filesystem: str = ""


def _unescape(value):
    return re.sub(r"\\([0-7]{3})", lambda match: chr(int(match[1], 8)), value)


def parse_mountinfo(text):
    mounts = {}
    for line in text.splitlines():
        fields = line.split()
        if len(fields) < 10 or "-" not in fields[6:]:
            raise ValueError("Invalid mount metadata")
        target = Path(_unescape(fields[4]))
        separator = fields.index("-", 6)
        if len(fields) < separator + 4:
            raise ValueError("Invalid mount metadata")
        mounts[target] = Mount(
            target, fields[2], _unescape(fields[3]), "ro" in fields[5].split(","), fields[separator + 1]
        )
    return mounts


def overlapping(first, second):
    left, right = PurePosixPath(first), PurePosixPath(second)
    return left.is_relative_to(right) or right.is_relative_to(left)
