"""Actual isolated runtime startup/authentication/worker/restore on both OSes."""

import json
import os
import subprocess
import sys
from pathlib import Path


def test_managed_runtime_proof_ignores_inherited_installation_and_foreign_cwd(tmp_path):
    script = Path(__file__).resolve().parents[1] / "scripts" / "portable_runtime_smoke.py"
    protected = tmp_path / "untouched-installation"
    protected.mkdir()
    database = protected / "database.sqlite3"
    database.write_bytes(b"Synthetic sentinel, never open as SQLite")
    working = tmp_path / "foreign-working-directory"
    working.mkdir()
    environment = dict(os.environ)
    environment.update(
        NOTENARCHIV_PROFILE="nas",
        NOTENARCHIV_LOCAL_ROOT=str(protected),
        SOURCE_DIR=str(protected),
        DATABASE_PATH=str(database),
        APP_BIND="0.0.0.0",
        DJANGO_SETTINGS_MODULE="tests.settings",
        DEBUG_MODE="TRUE",
        PRINT_ENABLED="1",
    )
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=working,
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )
    evidence = json.loads(result.stdout)
    assert evidence == {
        "result": "success",
        "scope": "synthetic shared runtime",
        "checks": ["initialization", "single_instance", "loopback", "auth_csrf", "worker_shutdown", "sqlite_restore"],
        "native_archive_storage": "not exercised",
        "packaged_desktop": "not exercised",
    }
    assert list(working.iterdir()) == []
    assert list(protected.iterdir()) == [database]
    assert database.read_bytes() == b"Synthetic sentinel, never open as SQLite"
    assert str(tmp_path) not in result.stdout + result.stderr
