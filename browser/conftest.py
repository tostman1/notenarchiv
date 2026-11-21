"""Use production-like file SQLite locking for concurrent browser/worker tests."""

import pytest
from django.db import connections


@pytest.fixture(scope="session")
def django_db_modify_db_settings(tmp_path_factory):
    # Shared-cache in-memory SQLite raises SQLITE_LOCKED immediately across
    # threads; it does not exercise the configured file DB busy timeout.
    configuration = connections["default"].settings_dict["TEST"]
    previous = configuration.get("NAME")
    configuration["NAME"] = str(tmp_path_factory.mktemp("browser-db") / "synthetic.sqlite3")
    yield
    configuration["NAME"] = previous
