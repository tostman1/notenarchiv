"""Independent migrated SQLite updates and restart retain saved defaults/overrides."""

import os
import subprocess
import sys


def test_saved_defaults_reopen_and_competing_refresh(tmp_path):
    env = os.environ.copy()
    env.update(
        DJANGO_SETTINGS_MODULE="config.settings",
        NOTENARCHIV_PROFILE="local",
        DEBUG_MODE="FALSE",
        NOTENARCHIV_LOCAL_ROOT=str(tmp_path / "roots"),
        DATABASE_PATH=str(tmp_path / "data" / "synthetic.sqlite3"),
    )
    subprocess.run(
        [sys.executable, "manage.py", "migrate", "--noinput"], env=env, check=True, capture_output=True, timeout=30
    )
    code = """
import django,threading
django.setup()
from concurrent.futures import ThreadPoolExecutor
from django.contrib.auth import get_user_model
from django.db import connections
from apps.projects import models as m,services as p,participant_services as s
from apps.catalog.models import Part,InstrumentVariant,Work,Arrangement
from apps.members.models import Member
actor=get_user_model().objects.create_user('synthetic-participant-persist')
variant=InstrumentVariant.objects.create(name='Synthetic',clef='BASS')
parts=[Part.objects.create(instrument=variant,code=str(n)) for n in (1,2)]
member=Member.objects.create(name='Synthetic member',regular_part=parts[0])
values=dict(name='Synthetic',layout='REGULAR',width_mm=170,height_mm=120,cover_enabled=True,cover_title='')
project=p.save_project(values,actor=actor)
s.member_subset(project.pk,[member.pk],scope_ids=[member.pk],actor=actor,expected_revision=1)
participant=project.participants.get()
slot=m.ProjectPosition.objects.create(project=project,order=1,arrangement=Arrangement.objects.create(work=Work.objects.create(title='Synthetic')))
m.PartOverride.objects.create(project=project,participant=participant,position=slot,desired_part=parts[0])
member.regular_part=parts[1];member.revision+=1;member.save()
participant.refresh_from_db();assert participant.default_part_id==parts[0].pk
barrier=threading.Barrier(2)
def refresh(_):
    barrier.wait(timeout=10)
    try:
        s.change_participant(project.pk,participant.pk,action='refresh',actor=actor.pk,expected_revision=2,expected_member_revision=member.revision)
        return 'saved'
    except p.ProjectConflict:
        return 'conflict'
    finally:
        connections.close_all()
with ThreadPoolExecutor(max_workers=2) as pool:
    results=list(pool.map(refresh,range(2)))
assert sorted(results)==['conflict','saved'],results
assert m.PartOverride.objects.get().desired_part_id==parts[0].pk
"""
    subprocess.run([sys.executable, "-c", code], env=env, check=True, capture_output=True, timeout=40)
    reopen = """
import django
django.setup()
from django.db import connection
from apps.projects import models as m
p=m.Project.objects.get();participant=p.participants.get()
assert p.revision==3 and participant.default_part.code=='2'
assert participant.member_revision==participant.member.revision
assert participant.overrides.get().desired_part.code=='1'
assert participant.history.count()==2
with connection.cursor() as cursor:
    assert cursor.execute('PRAGMA foreign_key_check').fetchall()==[]
    assert cursor.execute('PRAGMA integrity_check').fetchone()==('ok',)
"""
    subprocess.run([sys.executable, "-c", reopen], env=env, check=True, capture_output=True, timeout=30)
