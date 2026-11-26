"""Root pytest configuration.

Ensures the project root is importable so the ``config``/``apps``/``core``
packages and ``tests.settings`` resolve. The test environment itself is
prepared in tests/settings.py (pytest-django imports settings before any
conftest runs).
"""

from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(autouse=True)
def content_history_transactional_cleanup(request):
    """Protect history during all tests; permit only disposable DB teardown flush."""
    marker = request.node.get_closest_marker("django_db")
    if marker is None:
        yield
        return
    # Register Django teardown first so our guard cleanup runs before its flush.
    request.getfixturevalue("_django_db_helper")
    from django.db import connection

    tables = (
        import_module("apps.archive.migrations.0007_content_history_guards").TABLES
        + import_module("apps.archive.migrations.0009_content_confirmation_guards").TABLES
    )
    catalog_tables = (
        import_module("apps.catalog.migrations.0003_catalog_association_history").TABLES
        + import_module("apps.catalog.migrations.0005_association_current_guards").TABLES
    )
    with connection.cursor() as cursor:
        existing = set(connection.introspection.table_names(cursor))
        for table in tables:
            if table in existing:
                cursor.execute(
                    f"CREATE TRIGGER IF NOT EXISTS {table}_delete_guard BEFORE DELETE ON {table} "
                    "BEGIN SELECT RAISE(ABORT, 'immutable content history'); END"
                )
        for table in catalog_tables:
            if table in existing:
                cursor.execute(
                    f"CREATE TRIGGER IF NOT EXISTS {table}_immutable_delete BEFORE DELETE ON {table} "
                    "BEGIN SELECT RAISE(ABORT, 'Immutable catalog association history'); END"
                )
    yield
    if marker.kwargs.get("transaction"):
        with connection.cursor() as cursor:
            for table in tables:
                cursor.execute(f"DROP TRIGGER IF EXISTS {table}_delete_guard")
            for table in catalog_tables:
                cursor.execute(f"DROP TRIGGER IF EXISTS {table}_immutable_delete")
