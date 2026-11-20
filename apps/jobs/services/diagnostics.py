"""Read bounded, sanitized diagnostic pages from fixed service files only."""

import json
import os
import stat
from contextlib import suppress
from datetime import UTC, datetime
from uuid import UUID

from django.core import signing

from config.diagnostics import BACKUPS, COMPONENTS, EVENTS

LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
SOURCES = ("web", "worker")
SCAN_BYTES = 64 * 1024
MAX_LINE = 4096
SALT = "diagnostics.cursor.v1"


class InvalidCursor(ValueError):
    """A cursor is invalid, expired or belongs to another source."""


def sanitize_record(line, source):
    try:
        raw = json.loads(line)
        if not isinstance(raw, dict) or raw.get("service") != source or raw.get("level") not in LEVELS:
            return None
        timestamp = datetime.fromisoformat(raw["timestamp"])
        if timestamp.tzinfo is None:
            return None
        component = raw.get("component")
        if component not in COMPONENTS | {"django", "application"}:
            return None
        event = raw.get("event")
        clean = {
            "timestamp": timestamp.astimezone(UTC).isoformat(),
            "level": raw["level"],
            "service": source,
            "component": component,
            "event": event
            if isinstance(event, str) and event in EVENTS | {"diagnostic", "http_response"}
            else "diagnostic",
        }
        for name in ("job_id", "correlation_id", "file_id"):
            if isinstance(raw.get(name), str):
                with suppress(ValueError):
                    clean[name] = str(UUID(raw[name]))
        for name, lower, upper in (("duration_ms", 0, 2**63 - 1), ("status_code", 100, 599)):
            value = raw.get(name)
            if type(value) is int and lower <= value <= upper:
                clean[name] = value
        if raw.get("error") == "exception":
            clean["error"] = "exception"
        return clean
    except (ValueError, TypeError, KeyError, UnicodeDecodeError, OverflowError, RecursionError):
        return None


def _entries(directory, source):
    entries = []
    for suffix in [f".{number}" for number in range(BACKUPS, 0, -1)] + [""]:
        path = directory / f"{source}.debug.log{suffix}"
        try:
            info = path.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISREG(info.st_mode):
            entries.append((path, [info.st_dev, info.st_ino], info.st_size))
    return entries


def _decode_cursor(cursor, source):
    try:
        if len(cursor) > 2048:
            raise ValueError
        state = signing.loads(cursor, salt=SALT, max_age=3600)
        if (
            state["source"] != source
            or type(state["offset"]) is not int
            or not 0 <= state["offset"] <= 2**63 - 1
            or type(state["discard"]) is not bool
            or not isinstance(state["identity"], list)
            or len(state["identity"]) != 2
            or any(type(value) is not int for value in state["identity"])
        ):
            raise ValueError
        return state
    except (signing.BadSignature, ValueError, TypeError, KeyError) as exc:
        raise InvalidCursor from exc


def _matches(record, filters):
    for name in ("level", "component", "job_id"):
        if filters.get(name) and record.get(name) != str(filters[name]):
            return False
    timestamp = datetime.fromisoformat(record["timestamp"])
    return not (
        (filters.get("since") and timestamp < filters["since"])
        or (filters.get("until") and timestamp > filters["until"])
    )


def read_page(directory, filters, cursor="", *, budget=SCAN_BYTES, limit=100):
    """Read at most budget bytes / limit records; retain position across rotation.

    The initial view tails the current file. History starts at the oldest
    retained file. A lost rotation cursor resets explicitly to the current tail.
    Incomplete current records are retried after the next append.
    """
    source = filters["source"]
    if source not in SOURCES:
        raise ValueError("Invalid diagnostic source")
    state = _decode_cursor(cursor, source) if cursor else None
    entries = _entries(directory, source)
    if not entries:
        return {"records": [], "cursor": "", "more": False, "reset": bool(state)}
    index = next((i for i, entry in enumerate(entries) if state and entry[1] == state["identity"]), None)
    reset = bool(state and index is None)
    if index is None:
        index = 0 if filters.get("history") and not state else len(entries) - 1
        offset = 0 if filters.get("history") and not state else max(0, entries[index][2] - budget)
        discard = offset > 0
    else:
        offset, discard = state["offset"], state["discard"]
        if offset > entries[index][2]:
            offset, discard, reset = 0, False, True
    records, consumed = [], 0
    while index < len(entries):
        path, identity, _size = entries[index]
        try:
            flags = (
                os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0) | getattr(os, "O_NONBLOCK", 0)
            )
            fd = os.open(path, flags)
        except FileNotFoundError:
            return {"records": records, "cursor": "", "more": False, "reset": True}
        with os.fdopen(fd, "rb") as stream:
            actual = os.fstat(stream.fileno())
            if not stat.S_ISREG(actual.st_mode) or [actual.st_dev, actual.st_ino] != identity:
                return {"records": records, "cursor": "", "more": False, "reset": True}
            stream.seek(offset)
            while consumed < budget and len(records) < limit:
                start = stream.tell()
                cap = min(MAX_LINE, budget - consumed)
                line = stream.readline(cap)
                if not line:
                    break
                consumed += len(line)
                if not line.endswith(b"\n") and len(line) < MAX_LINE:
                    # Retry a partial current line, or move past a crashed writer's tail.
                    stream.seek(start)
                    break
                offset = stream.tell()
                if discard:
                    discard = not line.endswith(b"\n")
                    continue
                if not line.endswith(b"\n"):
                    discard = True
                    continue
                record = sanitize_record(line, source)
                if record and _matches(record, filters):
                    records.append(record)
            at_end = stream.tell() >= os.fstat(stream.fileno()).st_size
        if consumed >= budget or len(records) >= limit or index == len(entries) - 1:
            break
        # A partial final line in an old file cannot grow after rotation.
        index += 1
        offset, discard = 0, False
    state = {"source": source, "identity": entries[index][1], "offset": offset, "discard": discard}
    return {
        "records": records,
        "cursor": signing.dumps(state, salt=SALT, compress=True),
        "more": index < len(entries) - 1 or not at_end,
        "reset": reset,
    }
