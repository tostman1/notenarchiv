"""Independent migrated file-SQLite writers and restart preserve project identities."""

import os
import subprocess
import sys


def test_project_concurrent_settings_and_restart(tmp_path):
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
from apps.projects import models as m,services as s
actor=get_user_model().objects.create_user('synthetic-project-persist')
values=dict(name='Synthetic project',layout='REGULAR',width_mm=170,height_mm=120,cover_enabled=True,cover_title='')
project=s.save_project(values,actor=actor)
slot=m.ProjectPosition.objects.create(project=project,order=1)
barrier=threading.Barrier(2)
def save(name):
    barrier.wait(timeout=10)
    try:
        s.save_project(dict(values,name=name),actor=actor.pk,project_id=project.pk,expected_revision=1)
        return 'saved'
    except s.ProjectConflict:
        return 'conflict'
    finally:
        connections.close_all()
with ThreadPoolExecutor(max_workers=2) as pool:
    result=list(pool.map(save,['Synthetic one','Synthetic two']))
assert sorted(result)==['conflict','saved'],result
project.refresh_from_db()
assert project.revision==2 and project.history.count()==2
clone=s.duplicate_project(project.pk,name=project.name,actor=actor.pk,expected_revision=2)
assert clone.positions.get().pk!=slot.pk and clone.positions.get().arrangement_id is None
"""
    subprocess.run([sys.executable, "-c", code], env=env, check=True, capture_output=True, timeout=40)
    reopen = """
import django
django.setup()
from django.db import connection
from apps.projects import models as m
assert m.Project.objects.count()==2
source=m.Project.objects.get(duplicated_from__isnull=True)
clone=m.Project.objects.get(duplicated_from=source)
assert source.revision==2 and source.history.count()==2
assert clone.revision==1 and clone.positions.get().pk!=source.positions.get().pk
with connection.cursor() as cursor:
    assert cursor.execute('PRAGMA foreign_key_check').fetchall()==[]
    assert cursor.execute('PRAGMA integrity_check').fetchone()==('ok',)
"""
    subprocess.run([sys.executable, "-c", reopen], env=env, check=True, capture_output=True, timeout=30)
