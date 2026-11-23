from importlib import import_module

from django.db import migrations


def install(apps, schema_editor):
    # SQLite remakes nullable participant tables and the self-referenced snapshot.
    # Reinstall every affected invariant before exposing new output kinds.
    for module in ("0002_immutable_guards", "0007_artifact_guards"):
        guards = import_module("apps.exports.migrations." + module)
        guards.remove(apps, schema_editor)
        guards.install(apps, schema_editor)


class Migration(migrations.Migration):
    dependencies = [("exports", "0008_generationsnapshot_source_snapshot_and_more")]
    operations = [migrations.RunPython(install, migrations.RunPython.noop)]
