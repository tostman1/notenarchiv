"""Shared list atomic write races persist over independent process restart."""

import os
import subprocess
import sys


def test_file_sqlite_reorder_race_and_reopen(tmp_path):
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
from apps.projects import models as m,services as p,list_services as s
from apps.catalog.models import Work,Arrangement
actor=get_user_model().objects.create_user('synthetic-list-race')
project=p.save_project(dict(name='Synthetic',layout='REGULAR',width_mm=170,height_mm=120,cover_enabled=True,cover_title=''),actor=actor)
arr=Arrangement.objects.create(work=Work.objects.create(title='Synthetic piece'))
rows=[m.ProjectPosition.objects.create(project=project,order=i,arrangement=arr if i!=2 else None) for i in (1,2,3)]
barrier=threading.Barrier(2)
def reorder(order):
    barrier.wait(timeout=10)
    try:
        s.reorder(project.pk,order,actor=actor.pk,expected_revision=1)
        return 'saved'
    except p.ProjectConflict:
        return 'conflict'
    finally:
        connections.close_all()
with ThreadPoolExecutor(max_workers=2) as pool:
    result=list(pool.map(reorder,[[rows[2].pk,rows[0].pk,rows[1].pk],[r.pk for r in reversed(rows)]]))
assert sorted(result)==['conflict','saved'],result
assert list(s.positions(project).values_list('order',flat=True))==[1,2,3]
assert m.Project.objects.get(pk=project.pk).revision==2
"""
    subprocess.run([sys.executable, "-c", code], env=env, check=True, capture_output=True, timeout=40)
    reopen = """
import django
django.setup()
from django.db import connection
from apps.projects import models as m,list_services as s
p=m.Project.objects.get()
assert p.revision==2 and p.positions.count()==3 and p.history.count()==2
assert list(s.positions(p).values_list('order',flat=True))==[1,2,3]
assert p.positions.filter(arrangement__isnull=True).count()==1
assert m.PositionChange.objects.exists()
with connection.cursor() as cursor:
    assert cursor.execute('PRAGMA foreign_key_check').fetchall()==[]
    assert cursor.execute('PRAGMA integrity_check').fetchone()==('ok',)
"""
    subprocess.run([sys.executable, "-c", reopen], env=env, check=True, capture_output=True, timeout=30)
