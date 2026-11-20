"""Actual migrations and separate interpreter restarts retain synthetic master data."""

import json
import os
import subprocess
import sys


def test_master_data_survives_reopening_and_idempotent_migrations(tmp_path):
    environment = os.environ.copy()
    environment.update(
        DJANGO_SETTINGS_MODULE="config.settings",
        NOTENARCHIV_PROFILE="local",
        DEBUG_MODE="FALSE",
        NOTENARCHIV_LOCAL_ROOT=str(tmp_path / "synthetic-roots"),
        DATABASE_PATH=str(tmp_path / "synthetic.sqlite3"),
    )
    migrate = [sys.executable, "manage.py", "migrate", "--noinput"]
    subprocess.run(migrate, env=environment, check=True, capture_output=True, timeout=30)
    create_script = """
import django,json,sys
django.setup()
from apps.catalog.models import Work,Arrangement,InstrumentVariant,Part,InstrumentationTemplate,TemplatePart
from apps.catalog.services import save_record,apply_template
from apps.members.models import Member
w=save_record(Work(title='Synthetic persisted work'))
a=save_record(Arrangement(work=w))
i=save_record(InstrumentVariant(name='Synthetic instrument',transposition='C'))
p=save_record(Part(instrument=i,code='1'))
m=save_record(Member(name='Synthetic persisted member',regular_part=p))
t=save_record(InstrumentationTemplate(name='Synthetic template'))
save_record(TemplatePart(template=t,part=p,required=False))
apply_template(a.pk,t,expected_revision=a.revision)
sys.stdout.write(json.dumps({'member':str(m.pk),'part':str(p.pk),'arrangement':str(a.pk)}))
"""
    created = subprocess.run(
        [sys.executable, "-c", create_script], env=environment, check=True, capture_output=True, text=True, timeout=15
    )
    identities = json.loads(created.stdout)
    repeated = subprocess.run(migrate, env=environment, check=True, capture_output=True, text=True, timeout=30)
    assert "No migrations to apply" in repeated.stdout
    verify_script = """
import django,json,sys
django.setup()
from apps.catalog.models import Arrangement
from apps.members.models import Member
from django.db import connection
data=json.loads(sys.argv[1])
m=Member.objects.get(pk=data['member'])
a=Arrangement.objects.get(pk=data['arrangement'])
assert str(m.regular_part_id)==data['part'] and m.name=='Synthetic persisted member'
assert a.expectations_defined and not a.expected_parts.get().required
with connection.cursor() as cursor:
    assert cursor.execute('PRAGMA foreign_keys').fetchone()==(1,)
sys.stdout.write('Synthetic identity and assignments persisted')
"""
    verified = subprocess.run(
        [sys.executable, "-c", verify_script, json.dumps(identities)],
        env=environment,
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert "assignments persisted" in verified.stdout
