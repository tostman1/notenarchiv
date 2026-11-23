from django.db import migrations


def install(apps, schema_editor):
    if schema_editor.connection.vendor != "sqlite":
        raise RuntimeError("Snapshot protection requires the approved SQLite backend")
    for table in ("exports_generationsnapshot", "exports_snapshotinput", "exports_generationrun"):
        for action in ("UPDATE",):
            schema_editor.execute(f"""CREATE TRIGGER {table}_{action.lower()}_guard
                BEFORE {action} ON {table} BEGIN
                SELECT RAISE(ABORT, 'immutable generation history'); END""")
    for table, key, fields in (
        ("archive_archivefile", "archive_file_id", ("sha256", "byte_size", "source_version_id", "root_kind", "relative_path", "review_state", "revision")),
        ("archive_archiveassignment", "assignment_id", ("archive_file_id", "part_id", "state")),
        ("archive_sourceversion", "source_version_id", ("sha256", "byte_size", "source_file_id", "pdf_state", "page_info")),
    ):
        changed = " OR ".join(f"NEW.{field} IS NOT OLD.{field}" for field in fields)
        schema_editor.execute(f"""CREATE TRIGGER {table}_pin_guard BEFORE UPDATE ON {table}
            WHEN EXISTS (SELECT 1 FROM exports_snapshotinput WHERE {key}=OLD.id)
            AND ({changed}) BEGIN SELECT RAISE(ABORT, 'pinned generation input'); END""")


def remove(apps, schema_editor):
    for table in ("exports_generationsnapshot", "exports_snapshotinput", "exports_generationrun"):
        for action in ("update",):
            schema_editor.execute(f"DROP TRIGGER IF EXISTS {table}_{action}_guard")
    for table in ("archive_archivefile", "archive_archiveassignment", "archive_sourceversion"):
        schema_editor.execute(f"DROP TRIGGER IF EXISTS {table}_pin_guard")


class Migration(migrations.Migration):
    dependencies = [("exports", "0001_initial")]
    operations = [migrations.RunPython(install, remove)]
