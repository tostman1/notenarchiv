"""SQLite connection hygiene: foreign keys and busy timeout.

Django's SQLite backend enables the foreign_keys pragma through the
``foreign_keys`` backend option; the busy timeout is set on every new
connection (ARCHITECTURE.md: configure busy timeout and bounded retry;
avoid long transactions).
"""

from __future__ import annotations

from django.db.backends.signals import connection_created


def _apply_sqlite_pragmas(sender, connection, **_kwargs) -> None:
    if connection.vendor != "sqlite":
        return
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.execute("PRAGMA busy_timeout = 5000")


connection_created.connect(_apply_sqlite_pragmas, dispatch_uid="notenarchiv.sqlite_pragmas")
