"""Committed additive mapping batches survive a deterministic interruption."""

from importlib import import_module
from unittest.mock import patch
from uuid import UUID, uuid5

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from apps.archive.models import SourceDocument, SourceFile, SourceFolder


@pytest.mark.django_db(transaction=True)
def test_document_mapping_resumes_after_a_committed_batch():
    folder = SourceFolder.objects.create(relative_path="Synthetic recovery")
    sources = [
        SourceFile.objects.create(
            id=UUID(int=index + 1), folder=folder, relative_path=f"Synthetic recovery/{index}.pdf"
        )
        for index in range(105)
    ]
    migration = import_module("apps.archive.migrations.0007_content_history_guards")
    state = MigrationExecutor(connection).loader.project_state()
    document_model = state.apps.get_model("archive", "SourceDocument")
    queryset = type(document_model.objects.all())
    original = queryset.bulk_create
    calls = []

    def interrupted(self, objects, **kwargs):
        if self.model is document_model:
            calls.append(len(objects))
            if len(calls) == 2:
                raise RuntimeError("Synthetic interruption before the second mapping batch")
        return original(self, objects, **kwargs)

    with connection.schema_editor() as editor:
        with (
            patch.object(queryset, "bulk_create", interrupted),
            pytest.raises(RuntimeError, match="Synthetic interruption"),
        ):
            migration.backfill(state.apps, editor)
        assert SourceDocument.objects.count() == 100
        receipts = dict(SourceDocument.objects.values_list("source_file_id", "pk"))
        migration.backfill(state.apps, editor)
        migration.backfill(state.apps, editor)
    assert SourceDocument.objects.count() == 105
    assert calls == [100, 5]
    assert all(
        SourceDocument.objects.get(source_file_id=source).pk == identity for source, identity in receipts.items()
    )
    assert all(
        SourceDocument.objects.get(source_file=source).pk == uuid5(migration.NAMESPACE, str(source.pk))
        for source in sources
    )
    assert SourceFile.objects.count() == 105
