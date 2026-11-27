from django.db import migrations


def install(apps, schema_editor):
    if schema_editor.connection.vendor != "sqlite":
        raise RuntimeError("Project content pins require the approved SQLite backend")
    schema_editor.execute("""CREATE TRIGGER exports_project_content_update_guard
        BEFORE UPDATE ON exports_snapshotprojectcontentinput BEGIN
        SELECT RAISE(ABORT, 'immutable generation history'); END""")
    fields = ("sha256", "byte_size", "source_version_id", "root_kind", "relative_path", "review_state", "revision")
    changed = " OR ".join(f"NEW.{field} IS NOT OLD.{field}" for field in fields)
    schema_editor.execute(f"""CREATE TRIGGER archive_project_content_file_guard
        BEFORE UPDATE ON archive_archivefile WHEN ({changed}) AND EXISTS (
            SELECT 1 FROM exports_snapshotprojectcontentinput pin
            JOIN archive_contentconfirmation approval ON approval.id=pin.confirmation_id
            JOIN archive_contentinspection inspection ON inspection.id=approval.inspection_id
            JOIN archive_contentreference reference ON reference.revision_id=inspection.revision_id
            WHERE reference.archive_file_id=OLD.id
        ) BEGIN SELECT RAISE(ABORT, 'pinned generation content input'); END""")


def remove(apps, schema_editor):
    schema_editor.execute("DROP TRIGGER IF EXISTS exports_project_content_update_guard")
    schema_editor.execute("DROP TRIGGER IF EXISTS archive_project_content_file_guard")


class Migration(migrations.Migration):
    dependencies = [("exports", "0014_snapshotprojectcontentinput")]
    operations = [migrations.RunPython(install, remove)]
