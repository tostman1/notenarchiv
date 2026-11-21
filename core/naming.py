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


def part_filename(groups, identifier):
    """Retain complete ordinary part codes even when instrument labels are long."""
    if not groups or len(groups) > 1000 or not re.fullmatch(r"[0-9a-f]{32}", identifier):
        raise ValueError("Invalid combined part identity")
    total = sum(len(codes) for _label, codes in groups)
    if not 1 <= total <= 1000:
        raise ValueError("Invalid bounded part set")
    budget = (160 - 3 * (len(groups) - 1)) // len(groups)
    stems = []
    for label, codes in groups:
        joined = "-".join(codes)
        token = component(joined, maximum=160)
        remaining = budget - len(token.encode("utf-8")) - 1
        if len(joined.encode("utf-8")) > 60 or remaining < 16:
            break
        stems.append(component(label, maximum=min(160, remaining)) + " " + token)
    if len(stems) == len(groups):
        return " - ".join(stems) + ".pdf"
    # Large combined assignments cannot all fit a SMB component. The complete
    # controlled set stays in the DB; the count/UUID identifies the actual PDF.
    label = f"Kombiniert {total} Stimmen - {groups[0][0]}"
    return component(label, maximum=120) + "--" + identifier[:12] + ".pdf"


def with_suffix(path, identifier, number=0):
    if not re.fullmatch(r"[0-9a-f]{32}", identifier) or type(number) is not int or not 0 <= number < 100:
        raise ValueError("Invalid collision identity")
    path = PurePosixPath(path)
    suffix = identifier[:12] + (f"-{number}" if number else "")
    return str(path.with_name(component(path.stem, maximum=80) + "--" + suffix + ".pdf"))
