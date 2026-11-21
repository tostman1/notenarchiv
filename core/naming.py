"""Human-readable SMB-safe names; display metadata remains unchanged."""

import re
import unicodedata
from pathlib import PurePosixPath

RESERVED = re.compile(r"^(CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³])(?:\.|$)", re.IGNORECASE)


def component(value, *, maximum=100):
    if not isinstance(value, str) or not 16 <= maximum <= 160:
        raise ValueError("Invalid name component")
    value = unicodedata.normalize("NFKC", value)
    value = "".join(
        "_" if char in '<>:"/\\|?*' or unicodedata.category(char).startswith("C") else char for char in value
    )
    value = " ".join(value.split()).strip(" .") or "Unbekannt"
    if RESERVED.match(value):
        value = "_" + value
    value = value.encode("utf-8")[:maximum].decode("utf-8", errors="ignore").rstrip(" .")
    return value or "Unbekannt"


def pdf_name(value):
    return component(PurePosixPath(value).stem) + ".pdf"


def with_suffix(path, identifier, number=0):
    if not re.fullmatch(r"[0-9a-f]{32}", identifier) or type(number) is not int or not 0 <= number < 100:
        raise ValueError("Invalid collision identity")
    path = PurePosixPath(path)
    suffix = identifier[:12] + (f"-{number}" if number else "")
    return str(path.with_name(component(path.stem, maximum=80) + "--" + suffix + ".pdf"))
