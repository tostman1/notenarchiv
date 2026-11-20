"""Pytest fixtures for the Notenarchiv test suite.

Synthetic fixtures only: no real association music, member records or
database files may ever be committed (GR-14). Deterministic, generated
fixtures live in tests/fixtures/ when a test package needs them.
"""

from __future__ import annotations

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures"


@pytest.fixture()
def fixtures_dir() -> Path:
    """Path of the checked-in synthetic fixture directory (created lazily)."""
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    return FIXTURES_DIR
