"""Canonical relative references, distinct from filesystem authorization/opening."""

import re
import unicodedata
from pathlib import PurePosixPath


def relative_path(value, *, allow_root=False):
    if not isinstance(value, str) or len(value) > 1024:
        raise ValueError("Invalid relative path")
    if value == "" and allow_root:
        return value
    if (
        not value
        or value == "."
        or "\\" in value
        or re.match(r"^[A-Za-z]:", value)
        or any(unicodedata.category(char) in {"Cc", "Cs"} for char in value)
    ):
        raise ValueError("Invalid relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or str(path) != value or any(part in {".", ".."} for part in path.parts):
        raise ValueError("Invalid relative path")
    return value


def storage_key(value):
    """Managed destinations additionally reserve Unicode/case-equivalent names."""
    return unicodedata.normalize("NFKC", relative_path(value)).casefold()
