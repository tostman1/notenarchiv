"""Django settings for the test suite.

pytest-django imports the settings module before any conftest is loaded,
so the deterministic test environment must be prepared HERE, before the
main settings are imported. The suite runs in the explicitly selected
``local`` profile with a synthetic root under ``.dev/pytest``
(git-ignored): loopback-only, DEBUG=False, no real data (GR-14).

Production code and management commands always use ``config.settings``
directly; this module exists solely for tests.
"""

from __future__ import annotations

import os
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_TEST_LOCAL_ROOT = _PROJECT_ROOT / ".dev" / "pytest"

os.environ["NOTENARCHIV_PROFILE"] = "local"
os.environ["NOTENARCHIV_LOCAL_ROOT"] = str(_TEST_LOCAL_ROOT)
os.environ.setdefault("DEBUG_MODE", "FALSE")
# "testserver" is Django's test-client host; loopback hosts are kept so
# host validation stays active and is testable.
os.environ["APP_ALLOWED_HOSTS"] = "localhost,127.0.0.1,testserver"

# Synthetic roots must exist so worker-style writability checks pass.
for _sub in ("raw", "clean", "processed", "status", "export"):
    (_TEST_LOCAL_ROOT / _sub).mkdir(parents=True, exist_ok=True)

from config.settings import *  # noqa: E402,F401,F403
from config.settings import env  # noqa: E402,F401
