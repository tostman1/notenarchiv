"""Bounded technical diagnostics. Free-form log messages never enter either sink."""

import json
import logging
import os
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from uuid import UUID

MAX_BYTES = 10 * 1024 * 1024
BACKUPS = 5
COMPONENTS = {"accounts", "archive", "catalog", "exports", "jobs", "members", "printing", "projects"}
EVENTS = {"service_started", "job_started", "job_finished", "job_failed"}


class DiagnosticFormatter(logging.Formatter):
    def __init__(self, service):
        super().__init__()
        self.service = service

    def format(self, record):
        parts = record.name.split(".", 2)
        component = "application"
        if parts[0] == "django":
            component = "django"
        elif len(parts) > 1 and parts[0] == "apps" and parts[1] in COMPONENTS:
            component = parts[1]
        event = getattr(record, "event", None)
        data = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": logging.getLevelName(record.levelno) if record.levelno in (10, 20, 30, 40, 50) else "OTHER",
            "service": self.service,
            "component": component,
            "event": event if isinstance(event, str) and event in EVENTS else "diagnostic",
        }
        status = getattr(record, "status_code", None)
        if type(status) is int and 100 <= status <= 599:
            data["event"] = "http_response"
            data["status_code"] = status
        for key in ("job_id", "correlation_id", "file_id"):
            value = getattr(record, key, None)
            if isinstance(value, UUID):
                data[key] = str(value)
        duration = getattr(record, "duration_ms", None)
        if type(duration) is int and 0 <= duration <= 2**63 - 1:
            data["duration_ms"] = duration
        if record.exc_info:
            data["error"] = "exception"
        return json.dumps(data)


class SafeStreamHandler(logging.StreamHandler):
    def handleError(self, record):
        # The stdlib diagnostic on an I/O failure includes raw message arguments.
        os.write(2, b"Technical log output failed.\n")


class DebugFileHandler(RotatingFileHandler):
    handleError = SafeStreamHandler.handleError

    def __init__(self, directory, service):
        directory = Path(directory)
        directory.mkdir(exist_ok=True)
        # Keep a stable lock inode across rotation. OS releases it on process exit.
        self._writer = (directory / f"{service}.lock").open("a+b")
        try:
            if os.name == "nt":
                import msvcrt

                self._writer.seek(0)
                msvcrt.locking(self._writer.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(self._writer, fcntl.LOCK_EX | fcntl.LOCK_NB)
            super().__init__(
                directory / f"{service}.debug.log", maxBytes=MAX_BYTES, backupCount=BACKUPS, encoding="utf-8"
            )
        except BaseException:
            self._writer.close()
            raise

    def close(self):
        try:
            super().close()
        finally:
            self._writer.close()


def logging_config(debug_mode, service, directory, *, file_logging=True):
    level = "DEBUG" if debug_mode else "INFO"
    handlers = {
        "stdout": {"()": SafeStreamHandler, "stream": "ext://sys.stdout", "formatter": "technical", "level": level},
    }
    if debug_mode and file_logging:
        handlers["debug_file"] = {
            "()": DebugFileHandler,
            "directory": directory,
            "service": service,
            "formatter": "technical",
            "level": level,
        }
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {"technical": {"()": DiagnosticFormatter, "service": service}},
        "handlers": handlers,
        "root": {"handlers": list(handlers), "level": level},
        "loggers": {
            name: {"handlers": [], "level": "NOTSET", "propagate": True} for name in ("django", "django.server")
        },
    }
