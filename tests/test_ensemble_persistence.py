"""Actual file-SQLite role/mapping races and independent process reopen."""

import os
import subprocess
import sys


def test_mapping_concurrent_writers_and_restart(tmp_path):
    environment = os.environ.copy()
    environment.update(
        DJANGO_SETTINGS_MODULE="config.settings",
        NOTENARCHIV_PROFILE="local",
        DEBUG_MODE="FALSE",
        NOTENARCHIV_LOCAL_ROOT=str(tmp_path / "roots"),
        DATABASE_PATH=str(tmp_path / "data" / "synthetic.sqlite3"),
    )
    subprocess.run(
        [sys.executable, "manage.py", "migrate", "--noinput"],
        env=environment,
        check=True,
        capture_output=True,
        timeout=30,
    )
    create = """
import django,threading,uuid
django.setup()
from concurrent.futures import ThreadPoolExecutor
from django.contrib.auth import get_user_model
from django.db import connections
from apps.catalog.models import InstrumentVariant,Part
from apps.projects import models as m,services as p,ensemble_services as e
actor=get_user_model().objects.create_user('synthetic-ensemble-persist')
values=dict(name='Synthetic ensemble',layout='REGULAR',width_mm=170,height_mm=120,cover_enabled=True,cover_title='')
project=p.save_project(values,actor=actor)
variant=InstrumentVariant.objects.create(name='Synthetic Posaune',clef='BASS')
parts=[Part.objects.create(instrument=variant,code=str(n)) for n in (2,3)]
role=e.save_role(project.pk,code='3',label='Musical role',actor=actor,expected_revision=1)
person=m.ProjectParticipant.objects.create(project=project,guest_id=uuid.uuid4(),display_name='Synthetic',default_part=parts[0])
e.assign_role(project.pk,person.pk,role.pk,actor=actor,expected_revision=2)
barrier=threading.Barrier(2)
def save(part):
    barrier.wait(timeout=10)
    try:
        e.save_mapping(project.pk,role_id=role.pk,instrument_id=variant.pk,part_id=part.pk,
            actor=actor.pk,expected_revision=3)
        return 'saved'
    except p.ProjectConflict:
        return 'conflict'
    finally:
        connections.close_all()
with ThreadPoolExecutor(max_workers=2) as pool:
    results=list(pool.map(save,parts))
assert sorted(results)==['conflict','saved'],results
assert m.EnsembleMapping.objects.count()==1 and m.Project.objects.get().revision==4
"""
    subprocess.run([sys.executable, "-c", create], env=environment, check=True, capture_output=True, timeout=40)
    reopen = """
import django
django.setup()
from django.db import connection
from apps.projects import models as m,ensemble_services as e
p=m.Project.objects.get(); person=p.participants.get(); mapping=m.EnsembleMapping.objects.get()
choice=e.mapping_choice(p.pk,person.role_id,person.default_part.instrument_id)
assert choice.status=='MAPPED' and choice.mapping.pk==mapping.pk
assert p.revision==4 and p.history.count()==4 and p.ensemble_history.count()==3
with connection.cursor() as cursor:
    assert cursor.execute('PRAGMA foreign_key_check').fetchall()==[]
    assert cursor.execute('PRAGMA integrity_check').fetchone()==('ok',)
"""
    subprocess.run([sys.executable, "-c", reopen], env=environment, check=True, capture_output=True, timeout=30)
