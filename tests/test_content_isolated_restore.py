"""Private temporary SQLite restore of synthetic additive history only."""

import sqlite3

import pytest
from django.db import connection

from apps.archive.content_geometry_services import source_document
from apps.catalog.collection_services import add_membership
from apps.catalog.models import Collection, Work
from tests.test_content_geometry_models import page


@pytest.mark.django_db(transaction=True)
def test_sqlite_backup_restores_source_pins_provenance_and_guards(tmp_path):
    original = page(original=True)
    document = source_document(original.source_version.source_file_id)
    collection = Collection.objects.create(title="Synthetic restore", metadata={"publisher": "Fixture"})
    work = Work.objects.create(title="Synthetic movement")
    member = add_membership(collection.pk, work.pk, position=0)
    with connection.cursor() as cursor:
        cursor.execute("SELECT metadata_snapshot FROM catalog_collectionmembership WHERE id = %s", [member.pk.hex])
        expected_snapshot = cursor.fetchone()[0]
    destination = tmp_path / "isolated.sqlite3"
    with sqlite3.connect(destination) as restored:
        connection.connection.backup(restored)
        assert restored.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert restored.execute("PRAGMA foreign_key_check").fetchall() == []
        assert restored.execute("SELECT id FROM archive_sourcedocument").fetchone()[0] == document.pk.hex
        assert (
            restored.execute("SELECT geometry_fingerprint FROM archive_sourcepage").fetchone()[0]
            == original.geometry_fingerprint
        )
        assert (
            restored.execute("SELECT metadata_snapshot FROM catalog_collectionmembership").fetchone()[0]
            == expected_snapshot
        )
        with pytest.raises(sqlite3.IntegrityError, match="history"):
            restored.execute("DELETE FROM archive_sourcedocument")
        with pytest.raises(sqlite3.IntegrityError, match="history"):
            restored.execute("DELETE FROM catalog_collectionmembership")
    assert document.source_file_id == original.source_version.source_file_id
