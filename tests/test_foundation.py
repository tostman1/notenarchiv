"""Foundation smoke tests: interpreter baseline, Django pin, DEBUG_MODE contract.

WP-02 exercises the real project settings (see test_settings.py); the
isolated smoke-settings approach of WP-01 was replaced by the local test
profile configured in tests/conftest.py.
"""

from __future__ import annotations

import importlib.metadata
import sys

import pytest

from config.env import ConfigError, parse_debug_mode

EXPECTED_PYTHON_VERSION = (3, 12)


def test_interpreter_matches_baseline() -> None:
    """The foundation pins CPython 3.12; a dev interpreter outside the range
    means the lockfile/environment was synced with the wrong Python."""
    assert (sys.version_info.major, sys.version_info.minor) == EXPECTED_PYTHON_VERSION


def test_django_foundation_is_pinned() -> None:
    """Django 5.2 LTS is the framework baseline (ARCHITECTURE.md section 2)."""
    version = importlib.metadata.version("Django")
    assert version.startswith("5.2."), f"expected Django 5.2 LTS, got {version}"


@pytest.mark.parametrize(
    "raw,expected",
    [
        (None, False),
        ("", None),
        ("FALSE", False),
        ("false", False),
        (" False ", False),
        ("TRUE", True),
        ("true", True),
        (" True ", True),
        ("maybe", None),
        ("1", None),
    ],
)
def test_debug_mode_env_contract(raw: str | None, expected: bool | None) -> None:
    """OP-04 contract: DEBUG_MODE absent or FALSE (trimmed, case-insensitive)
    => Deploy (False); TRUE => application diagnostics (True). Any other value,
    including explicitly empty, fails clearly (WP-02 full behavior)."""
    if expected is None:
        with pytest.raises(ConfigError):
            parse_debug_mode(raw)
    else:
        assert parse_debug_mode(raw) is expected
