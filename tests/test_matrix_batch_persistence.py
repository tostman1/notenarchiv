"""Actual competing SQLite batch writes and independent reset/save reopen."""

import os
import subprocess
import sys


def test_batch_race_reset_and_independent_reopen(tmp_path):
    from tests.test_resolution_persistence import test_resolver_independent_migration_and_reopen

    test_resolver_independent_migration_and_reopen(tmp_path)
    env = os.environ.copy()
    env.update(
        DJANGO_SETTINGS_MODULE="config.settings",
        NOTENARCHIV_PROFILE="local",
        DEBUG_MODE="FALSE",
        NOTENARCHIV_LOCAL_ROOT=str(tmp_path / "roots"),
        DATABASE_PATH=str(tmp_path / "data" / "synthetic.sqlite3"),
    )
    race = """
import django,threading
django.setup()
from concurrent.futures import ThreadPoolExecutor
from django.contrib.auth import get_user_model
from django.db import connections
from apps.archive.models import ArchiveAssignment
from apps.projects import models as m,matrix_batch_services as b,matrix_edit_services as s,services as p
project=m.Project.objects.get();slot=project.positions.get();person=project.participants.get()
second=m.ProjectPosition.objects.create(project=project,order=2,arrangement=slot.arrangement)
actor=get_user_model().objects.get(username='synthetic-resolver-persist')
assignment=ArchiveAssignment.objects.usable().get();token=s.choice_token(assignment,actor)
choices=[(slot.pk,token),(second.pk,token)];barrier=threading.Barrier(2)
def save(_):
    barrier.wait(timeout=10)
    try:
        b.set_cells(project.pk,person.pk,choices,part_id=assignment.part_id,actor=actor,expected_revision=1)
        return 'saved'
    except p.ProjectConflict:
        return 'conflict'
    finally:
        connections.close_all()
with ThreadPoolExecutor(max_workers=2) as pool:
    result=list(pool.map(save,range(2)))
assert sorted(result)==['conflict','saved'],result
assert m.MatrixChange.objects.count()==2 and m.PartOverride.objects.filter(active=True).count()==2
b.reset_cells(project.pk,person.pk,[slot.pk],actor=actor,expected_revision=2)
"""
    subprocess.run([sys.executable, "-c", race], env=env, check=True, capture_output=True, timeout=45)
    reopen = """
import django
django.setup()
from apps.projects import models as m,resolution_services as r
project=m.Project.objects.get();person=project.participants.get()
reset=m.PartOverride.objects.get(active=False);saved=m.PartOverride.objects.get(active=True)
a=r.resolve_cell(project.pk,reset.position_id,person.pk);b=r.resolve_cell(project.pk,saved.position_id,person.pk)
assert a.usable and a.part_origin=='SAVED_DEFAULT' and a.override_id is None
assert b.usable and b.edition_origin=='PERSONAL' and b.assignment_id==saved.edition_id
assert reset.edition_id==saved.edition_id and project.revision==3 and project.positions.count()==2
assert m.MatrixChange.objects.get(event='OVERRIDE_RESET').previous_edition_id==reset.edition_id
"""
    subprocess.run([sys.executable, "-c", reopen], env=env, check=True, capture_output=True, timeout=30)
