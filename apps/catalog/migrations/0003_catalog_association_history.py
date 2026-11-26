from django.db import migrations

TABLES = (
    "catalog_collectionmembership",
    "catalog_workrelationship",
    "catalog_workalternativetitle",
)


def install(apps, schema_editor):
    if schema_editor.connection.vendor != "sqlite":
        return
    for table in TABLES:
        for operation in ("update", "delete"):
            schema_editor.execute(
                f"CREATE TRIGGER {table}_immutable_{operation} BEFORE {operation.upper()} ON {table} "
                "BEGIN SELECT RAISE(ABORT, 'Immutable catalog association history'); END"
            )


def remove(apps, schema_editor):
    if schema_editor.connection.vendor != "sqlite":
        return
    for table in TABLES:
        for operation in ("update", "delete"):
            schema_editor.execute(f"DROP TRIGGER IF EXISTS {table}_immutable_{operation}")


class Migration(migrations.Migration):
    dependencies = [("catalog", "0002_collection_workalternativetitle_collectionmembership_and_more")]
    operations = [migrations.RunPython(install, remove)]
