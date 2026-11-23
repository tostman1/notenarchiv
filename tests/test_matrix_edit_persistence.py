"""Actual SQLite competing manual cell writes and independent exact-choice reopen."""

import os
import subprocess
import sys


def test_manual_cell_race_and_restart(tmp_path):
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
    # Reuse the deterministic confirmed-copy restart fixture; append only the
    # approved manual edit race, without duplicating a new publication subsystem.
    from tests.test_resolution_persistence import test_resolver_independent_migration_and_reopen

    setup = tmp_path / "setup"
    test_resolver_independent_migration_and_reopen(setup)
    env["NOTENARCHIV_LOCAL_ROOT"] = str(setup / "roots")
    env["DATABASE_PATH"] = str(setup / "data" / "synthetic.sqlite3")
    code = """
import django,threading
django.setup()
from concurrent.futures import ThreadPoolExecutor
from django.contrib.auth import get_user_model
from django.db import connections
from apps.archive.models import ArchiveAssignment
from apps.projects import models as m,matrix_edit_services as s,services as p
project=m.Project.objects.get();slot=project.positions.get();person=project.participants.get()
actor=get_user_model().objects.get(username='synthetic-resolver-persist')
token=s.choice_token(ArchiveAssignment.objects.usable().get(),actor)
barrier=threading.Barrier(2)
def save(_):
    barrier.wait(timeout=10)
    try:
        s.set_cell(project.pk,slot.pk,person.pk,token,actor=actor,expected_revision=1)
        return 'saved'
    except p.ProjectConflict:
        return 'conflict'
    finally:
        connections.close_all()
with ThreadPoolExecutor(max_workers=2) as pool:
    result=list(pool.map(save,range(2)))
assert sorted(result)==['conflict','saved'],result
assert m.MatrixChange.objects.count()==1
"""
    subprocess.run([sys.executable, "-c", code], env=env, check=True, capture_output=True, timeout=40)
    reopen = """
import django
django.setup()
from apps.projects import models as m,resolution_services as r
project=m.Project.objects.get();override=m.PartOverride.objects.get()
result=r.resolve_cell(project.pk,override.position_id,override.participant_id)
assert result.usable and result.edition_origin=='PERSONAL' and result.assignment_id==override.edition_id
assert project.revision==2 and project.positions.count()==1
assert m.MatrixChange.objects.get().selected_edition_id==override.edition_id
"""
    subprocess.run([sys.executable, "-c", reopen], env=env, check=True, capture_output=True, timeout=30)
