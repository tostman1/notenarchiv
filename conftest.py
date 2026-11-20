"""Root pytest configuration.

Ensures the project root is importable so the ``config``/``apps``/``core``
packages and ``tests.settings`` resolve. The test environment itself is
prepared in tests/settings.py (pytest-django imports settings before any
conftest runs).
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
