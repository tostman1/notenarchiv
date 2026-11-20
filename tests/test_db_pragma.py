"""SQLite integrity tests: foreign keys and busy timeout (ARCHITECTURE.md section 5)."""

from __future__ import annotations

import pytest
from django.db import connection


@pytest.mark.django_db
def test_sqlite_foreign_keys_pragma_is_on() -> None:
    """Foreign keys must be enforced on every connection (ARCHITECTURE.md:
    enable foreign keys)."""
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA foreign_keys")
        (enabled,) = cursor.fetchone()
    assert enabled == 1


@pytest.mark.django_db
def test_sqlite_busy_timeout_is_configured() -> None:
    """A bounded busy timeout prevents immediate 'database is locked'
    failures under short concurrent access."""
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA busy_timeout")
        (timeout,) = cursor.fetchone()
    assert timeout == 5000
