from importlib import import_module

from django.db import migrations


def install(apps, schema_editor):
    # SQLite table recreation in 0003 drops triggers attached to that table.
    guards = import_module("apps.exports.migrations.0002_immutable_guards")
    guards.remove(apps, schema_editor)
    guards.install(apps, schema_editor)
    for table in ("exports_snapshotparticipant", "exports_snapshotposition"):
        schema_editor.execute(f"""CREATE TRIGGER {table}_update_guard BEFORE UPDATE ON {table}
            BEGIN SELECT RAISE(ABORT, 'immutable generation history'); END""")


def remove(apps, schema_editor):
    for table in ("exports_snapshotparticipant", "exports_snapshotposition"):
        schema_editor.execute(f"DROP TRIGGER IF EXISTS {table}_update_guard")


class Migration(migrations.Migration):
    dependencies = [("exports", "0003_generationsnapshot_request_id_snapshotparticipant_and_more")]
    operations = [migrations.RunPython(install, remove)]
