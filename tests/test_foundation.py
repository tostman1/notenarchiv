"""Foundation smoke tests for WP-01.

These tests verify that the locked Python/Django foundation imports cleanly
and that a minimal Django settings module can initialize the framework.
They are not application tests: no views, models or business logic exist
in this work package (see IMPLEMENTATION_PLAN.md, WP-01).
"""

from __future__ import annotations

import importlib.metadata
import os
import sys
from pathlib import Path

import pytest

# The isolated smoke settings module lives next to these tests; make it
# importable regardless of how pytest was invoked (WP-02 adds the real
# project settings package under config/).
TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

import django  # noqa: E402

EXPECTED_PYTHON_MINOR = 12
EXPECTED_PYTHON_MAJOR = 3


def test_interpreter_matches_baseline() -> None:
    """The foundation pins CPython 3.12; a dev interpreter outside the range
    means the lockfile/environment was synced with the wrong Python."""
    assert (sys.version_info.major, sys.version_info.minor) == (EXPECTED_PYTHON_MAJOR, EXPECTED_PYTHON_MINOR)


def test_django_foundation_is_pinned() -> None:
    """Django 5.2 LTS is the framework baseline (ARCHITECTURE.md section 2)."""
    version = importlib.metadata.version("Django")
    assert version.startswith("5.2."), f"expected Django 5.2 LTS, got {version}"


def test_django_application_initializes() -> None:
    """A minimal, isolated settings module must initialize the Django
    application (settings + app registry) without errors."""
    os.environ["DJANGO_SETTINGS_MODULE"] = "smoke_settings"

    django.setup()
    from django.conf import settings

    assert settings.DEBUG is False  # invariant: Django DEBUG is always False (GR-13)
    # The app registry loaded the minimal default applications.
    from django.apps import apps

    labels = {app.label for app in apps.get_app_configs()}
    assert "auth" in labels
    assert "contenttypes" in labels


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("", False),
        ("FALSE", False),
        ("true", True),
        (" True ", True),
        ("False", False),
    ],
)
def test_debug_mode_env_contract(raw: str, expected: bool) -> None:
    """OP-04 mode contract: DEBUG_MODE absent or FALSE => Deploy; TRUE (case/
    whitespace-insensitive) => application diagnostics. The parse helper is
    exercised directly; WP-02 owns the full invalid-value failure behavior."""
    import smoke_settings  # noqa: PLC0415

    value = None if raw == "" else raw
    assert smoke_settings.parse_debug_mode(value) is expected
