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
from tests.test_editions import edition_inputs  # noqa: F401 - shared synthetic edition fixture
from tests.test_projects import project_inputs  # noqa: F401 - shared synthetic project graph

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture()
def fixtures_dir() -> Path:
    """Path of the checked-in synthetic fixture directory (created lazily)."""
    fixtures = PROJECT_ROOT / "tests" / "fixtures"
    fixtures.mkdir(parents=True, exist_ok=True)
    return fixtures


@pytest.fixture(autouse=True)
def content_history_transactional_cleanup(request):
    """Keep DELETE guards active in tests, permit pytest's disposable DB flush."""
    marker = request.node.get_closest_marker("django_db")
    if marker is None:
        yield
        return
    request.getfixturevalue("_django_db_helper")
    from importlib import import_module

    from django.db import connection

    tables = (
        import_module("apps.archive.migrations.0007_content_history_guards").TABLES
        + import_module("apps.archive.migrations.0009_content_confirmation_guards").TABLES
    )
    catalog_tables = import_module("apps.catalog.migrations.0003_catalog_association_history").TABLES
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
