"""Protect additive history from bulk mutation and backfill stable document IDs."""

from uuid import UUID, uuid5

from django.db import migrations, transaction

NAMESPACE = UUID("0ec6afc5-f96f-4e47-905a-3650b59e9411")
TABLES = (
    "archive_sourcedocument",
    "archive_pageregion",
    "archive_pageregionrevision",
    "archive_logicalpage",
    "archive_logicalpagerevision",
)


def backfill(apps, schema_editor):
    using = schema_editor.connection.alias
    sources = apps.get_model("archive", "SourceFile").objects.using(using)
    documents = apps.get_model("archive", "SourceDocument").objects.using(using)
    last = None
    while True:
        query = sources.order_by("pk") if last is None else sources.filter(pk__gt=last).order_by("pk")
        batch = list(query.values_list("pk", flat=True)[:100])
        if not batch:
            break
        with transaction.atomic(using=using):
            existing = set(documents.filter(source_file_id__in=batch).values_list("source_file_id", flat=True))
            documents.bulk_create(
                [
                    documents.model(id=uuid5(NAMESPACE, str(pk)), source_file_id=pk)
                    for pk in batch
                    if pk not in existing
                ],
                batch_size=100,
            )
        last = batch[-1]


def install(apps, schema_editor):
    if schema_editor.connection.vendor != "sqlite":
        raise RuntimeError("Content history requires the approved SQLite backend.")
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
    atomic = False
    dependencies = [("archive", "0006_logicalpage_pageregion_pageregionrevision_and_more")]
    operations = [
        migrations.RunPython(backfill, migrations.RunPython.noop),
        migrations.RunPython(install, remove),
    ]
