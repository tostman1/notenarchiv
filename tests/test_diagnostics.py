"""Use fresh processes so diagnostic configuration never replaces pytest's own handlers."""

import json
import logging
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from config.diagnostics import BACKUPS, MAX_BYTES, DebugFileHandler

PROBE = """
import logging, logging.config, sys
from pathlib import Path
from uuid import UUID
from config.diagnostics import logging_config
directory, service, mode = sys.argv[1:]
logging.config.dictConfig(logging_config(mode == "debug", service, Path(directory)))
log = logging.getLogger("django.server")
log.debug("synthetic OCR")
try:
    raise ValueError("synthetic password")
except ValueError:
    log.exception("cookie=%s", "synthetic token", extra={
        "event": "job_failed", "job_id": UUID(int=1), "file_id": "synthetic path", "duration_ms": 23,
    })
"""


class DiagnosticsTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.directory = Path(tmp.name) / "logs"

    def probe(self, mode="debug", service="web", check=True):
        return subprocess.run(
            [sys.executable, "-c", PROBE, str(self.directory), service, mode],
            check=check,
            capture_output=True,
            text=True,
            timeout=10,
        )

    def test_deploy_stdout_only_and_sanitized(self):
        result = self.probe("deploy")
        self.assertEqual(result.stderr, "")
        self.assertFalse(self.directory.exists())
        record = json.loads(result.stdout)
        self.assertEqual(record["event"], "job_failed")
        self.assertEqual(record["duration_ms"], 23)
        self.assertEqual(record["component"], "django")
        self.assertEqual(record["job_id"], "00000000-0000-0000-0000-000000000001")
        self.assertNotIn("file_id", record)
        self.assertNotIn("synthetic", result.stdout)

    def test_debug_persists_across_restart_and_mode_change(self):
        result = self.probe()
        path = self.directory / "web.debug.log"
        initial = path.read_text()
        self.assertEqual(initial, result.stdout)
        self.assertEqual([json.loads(line)["level"] for line in initial.splitlines()], ["DEBUG", "ERROR"])
        self.assertNotIn("synthetic", initial)
        self.probe("deploy")
        self.assertEqual(path.read_text(), initial)
        self.probe()
        self.assertTrue(path.read_text().startswith(initial))
        self.assertEqual(len(path.read_text().splitlines()), 4)

    def test_concurrent_writer_rejected_and_worker_independent(self):
        handler = DebugFileHandler(self.directory, "web")
        try:
            self.assertNotEqual(self.probe(check=False).returncode, 0)
            self.probe(service="worker")
            self.assertTrue((self.directory / "worker.debug.log").is_file())
        finally:
            handler.close()
        self.probe()

    def test_rotation_and_retention(self):
        handler = DebugFileHandler(self.directory, "worker")
        try:
            self.assertEqual(handler.maxBytes, MAX_BYTES)
            self.assertEqual(handler.backupCount, BACKUPS)
            handler.maxBytes = 5
            for index in range(9):
                record = logging.LogRecord("test", logging.INFO, "", 0, f"row{index}", (), None)
                handler.emit(record)
        finally:
            handler.close()
        files = sorted(self.directory.glob("worker.debug.log*"))
        self.assertEqual([path.read_text().strip() for path in files], [f"row{i}" for i in range(8, 2, -1)])

    def test_unusable_debug_directory_fails_startup(self):
        self.directory.touch()
        self.assertIn("debug_file", self.probe(check=False).stderr)
