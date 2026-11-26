"""Retain ordered proposals, relational pins, inspections and confirmations."""

from django.db import migrations

TABLES = (
    "archive_contentedition",
    "archive_contenteditionrevision",
    "archive_contentreference",
    "archive_contentinspection",
    "archive_contentconfirmation",
)


def install(apps, schema_editor):
    if schema_editor.connection.vendor != "sqlite":
        raise RuntimeError("Content confirmation requires the approved SQLite backend.")
    for table in TABLES:
        for action in ("UPDATE", "DELETE"):
            schema_editor.execute(
                f"CREATE TRIGGER {table}_{action.lower()}_guard BEFORE {action} ON {table} "
                "BEGIN SELECT RAISE(ABORT, 'immutable content history'); END"
            )


def remove(apps, schema_editor):
    for table in TABLES:
        for action in ("update", "delete"):
            schema_editor.execute(f"DROP TRIGGER IF EXISTS {table}_{action}_guard")


class Migration(migrations.Migration):
    dependencies = [("archive", "0008_contentedition_contenteditionrevision_and_more")]
    operations = [migrations.RunPython(install, remove)]
