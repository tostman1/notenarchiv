"""Resumable additive document identities survive schema-compatible restoration."""

from importlib import import_module

import pytest
from django.core.management import call_command
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from apps.archive import models as m
from apps.archive.content_geometry_services import source_document
from tests.test_content_geometry_models import page

SCHEMA = ("archive", "0006_logicalpage_pageregion_pageregionrevision_and_more")
BACKFILL = ("archive", "0007_content_history_guards")


@pytest.mark.django_db(transaction=True)
def test_document_backfill_reuses_partial_receipts_and_rebuilds():
    latest = MigrationExecutor(connection).loader.graph.leaf_nodes()
    try:
        MigrationExecutor(connection).migrate([SCHEMA])
        first = page()
        identity = source_document(first.source_version.source_file_id).pk
        folder = m.SourceFolder.objects.create(relative_path="Other synthetic")
        second = m.SourceFile.objects.create(folder=folder, relative_path="Other synthetic/second.pdf")
        MigrationExecutor(connection).migrate([BACKFILL])
        assert m.SourceDocument.objects.get(source_file=first.source_version.source_file).pk == identity
        second_id = m.SourceDocument.objects.get(source_file=second).pk
        # Re-running the bounded backfill preserves existing receipts.
        migration = import_module("apps.archive.migrations.0007_content_history_guards")
        apps = MigrationExecutor(connection).loader.project_state([BACKFILL]).apps
        with connection.schema_editor() as editor:
            migration.backfill(apps, editor)
        assert m.SourceDocument.objects.count() == 2
        # Schema-compatible rollback removes guards; reapplication preserves IDs.
        MigrationExecutor(connection).migrate([SCHEMA])
        MigrationExecutor(connection).migrate([BACKFILL])
        assert m.SourceDocument.objects.get(source_file=second).pk == second_id
        assert m.SourceVersion.objects.get(pk=first.source_version_id).sha256 == "a" * 64
    finally:
        # Only the disposable test database is cleared, with guards rolled back.
        MigrationExecutor(connection).migrate([SCHEMA])
        call_command("flush", verbosity=0, interactive=False)
        MigrationExecutor(connection).migrate(latest)
