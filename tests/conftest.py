"""Pytest fixtures for the Notenarchiv test suite.

The deterministic test environment (local profile, synthetic roots) is
configured in the root conftest.py before Django settings are imported.
Synthetic fixtures only: no real association music, member records or
database files may ever be committed (GR-14).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.archive_fixtures import archive  # noqa: F401 - shared pytest fixture

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture()
def fixtures_dir() -> Path:
    """Path of the checked-in synthetic fixture directory (created lazily)."""
    fixtures = PROJECT_ROOT / "tests" / "fixtures"
    fixtures.mkdir(parents=True, exist_ok=True)
    return fixtures
