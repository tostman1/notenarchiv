"""Retain terminal events and enforce unique positions among current associations."""

from importlib import import_module

from django.db import migrations

TABLES = ("catalog_associationwithdrawal",)


def install(apps, schema_editor):
    if schema_editor.connection.vendor != "sqlite":
        raise RuntimeError("Association history requires SQLite.")
    history = import_module("apps.catalog.migrations.0003_catalog_association_history")
    history.remove(apps, schema_editor)
    history.install(apps, schema_editor)
    for operation in ("update", "delete"):
        schema_editor.execute(
            f"CREATE TRIGGER catalog_associationwithdrawal_immutable_{operation} "
            f"BEFORE {operation.upper()} ON catalog_associationwithdrawal "
            "BEGIN SELECT RAISE(ABORT, 'Immutable catalog association history'); END"
        )
    for table, field, scope in (
        ("catalog_collectionmembership", "membership_id", "prior.collection_id = NEW.collection_id AND prior.position = NEW.position"),
        ("catalog_workrelationship", "relationship_id", "prior.parent_id = NEW.parent_id AND prior.kind = NEW.kind AND prior.position = NEW.position"),
    ):
        schema_editor.execute(
            f"CREATE TRIGGER {table}_current_position BEFORE INSERT ON {table} "
            f"WHEN EXISTS (SELECT 1 FROM {table} prior WHERE {scope} AND NOT EXISTS "
            f"(SELECT 1 FROM catalog_associationwithdrawal event WHERE event.{field} = prior.id)) "
            "BEGIN SELECT RAISE(ABORT, 'Active association position is occupied'); END"
        )


def remove(apps, schema_editor):
    for operation in ("update", "delete"):
        schema_editor.execute(f"DROP TRIGGER IF EXISTS catalog_associationwithdrawal_immutable_{operation}")
    for table in ("catalog_collectionmembership", "catalog_workrelationship"):
        schema_editor.execute(f"DROP TRIGGER IF EXISTS {table}_current_position")


class Migration(migrations.Migration):
    dependencies = [("catalog", "0004_associationwithdrawal_and_more")]
    operations = [migrations.RunPython(install, remove)]
