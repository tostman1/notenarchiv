from django.db import migrations


def seed(apps, schema_editor):
    apps.get_model("projects", "GlobalRuleState").objects.using(schema_editor.connection.alias).get_or_create(pk=1)


class Migration(migrations.Migration):
    dependencies = [("projects", "0008_positioneditionpreference_active_and_more")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
