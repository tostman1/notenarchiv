from django.db import migrations


TABLES = ("exportartifact", "exportpublication", "exportstage", "exportcompletion")


def install(apps, schema_editor):
    if schema_editor.connection.vendor != "sqlite":
        raise RuntimeError("Export protection requires SQLite")
    for name in TABLES:
        table = "exports_" + name
        for action in ("update",):
            schema_editor.execute(f"""CREATE TRIGGER {table}_{action}_guard
                BEFORE {action.upper()} ON {table} BEGIN
                SELECT RAISE(ABORT, 'immutable export history'); END""")


def remove(apps, schema_editor):
    for name in TABLES:
        for action in ("update",):
            schema_editor.execute(f"DROP TRIGGER IF EXISTS exports_{name}_{action}_guard")


class Migration(migrations.Migration):
    dependencies = [("exports", "0006_exportcompletion_exportpublication_exportstage_and_more")]
    operations = [migrations.RunPython(install, remove)]
