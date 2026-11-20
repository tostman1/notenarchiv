"""Minimal, isolated Django settings for the WP-01 foundation smoke tests.

This module is test-only. It proves the locked Django foundation can
initialize the app registry with a deliberately small app set. The real
application settings (environment parsing, security, static files, database
locations) are implemented in WP-02 under config/.

DEBUG is always False: the GR-13 invariant that DEBUG_MODE never enables
Django DEBUG is established at the settings level from day one.
"""

from __future__ import annotations

import os

SECRET_KEY = "notenarchiv-smoke-test-placeholder"

DEBUG = False  # Django DEBUG is always False (GR-13), in every mode.


def parse_debug_mode(raw: str | None) -> bool:
    """Parse the DEBUG_MODE environment variable per the OP-04 contract.

    Absent (None) or FALSE (trimmed, case-insensitive) => Deploy (False).
    TRUE => application diagnostics (True). Any other value raises
    ValueError so misconfiguration fails clearly instead of silently
    degrading to a default.
    """
    if raw is None:
        return False
    normalized = raw.strip().upper()
    if normalized not in {"TRUE", "FALSE"}:
        raise ValueError(f"DEBUG_MODE must be TRUE or FALSE, got {raw!r}")
    return normalized == "TRUE"


DEBUG_MODE = parse_debug_mode(os.environ.get("DEBUG_MODE"))

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

USE_TZ = True

TIME_ZONE = "Europe/Vienna"
