"""File-backed SQLite snapshot reopen; project edits cannot change historical inputs."""

import os
import subprocess
import sys


def test_authorization_survives_independent_process_reopen(tmp_path):
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
    create = """
import django
django.setup()
from django.contrib.auth import get_user_model
from apps.projects.models import Project
from apps.projects.preflight_services import build_report,report_token
from apps.exports.snapshot_services import authorize
p=Project.objects.get();a=get_user_model().objects.get(username='synthetic-resolver-persist')
r=build_report(p.pk)
run=authorize(p.pk,participant_ids=list(r.session.participants),position_ids=list(r.session.positions),
              token=report_token(r,a),acknowledgements=sorted(r.missing_keys),actor=a)
assert run.snapshot.inputs.count()==1 and run.job.status=='QUEUED'
Project.objects.filter(pk=p.pk).update(name='Changed synthetic after enqueue',revision=2)
"""
    subprocess.run([sys.executable, "-c", create], env=env, check=True, capture_output=True, timeout=60)
    reopen = """
import django
django.setup()
from apps.exports.models import GenerationRun
from apps.exports.snapshot_services import load_pinned_inputs
run=GenerationRun.objects.get();s,pins=load_pinned_inputs(run.snapshot_id)
assert s.project_revision==1 and len(pins)==1 and run.job.status=='QUEUED'
assert s.payload['project_name']!='Changed synthetic after enqueue'
"""
    subprocess.run([sys.executable, "-c", reopen], env=env, check=True, capture_output=True, timeout=30)


def test_concurrent_authorization_replay_creates_one_job(tmp_path):
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
    script = """
import django,threading
django.setup()
from concurrent.futures import ThreadPoolExecutor
from django.contrib.auth import get_user_model
from django.db import connections
from apps.projects.models import Project
from apps.projects.preflight_services import build_report,report_token
from apps.exports import snapshot_services as s
from apps.exports.models import GenerationRun
from apps.jobs.models import Job
p=Project.objects.get();a=get_user_model().objects.get(username='synthetic-resolver-persist')
from apps.catalog.models import Part
person=p.participants.get()
missing=Part.objects.create(instrument=person.default_part.instrument,code='synthetic-missing')
type(person).objects.filter(pk=person.pk).update(default_part=missing)
r=build_report(p.pk);token=report_token(r,a);barrier=threading.Barrier(2)
original=s.build_report
def build(*args,**kwargs):
    report=original(*args,**kwargs);barrier.wait(timeout=20);return report
s.build_report=build
def enqueue(_):
    try:
        return str(s.authorize(p.pk,participant_ids=list(r.session.participants),position_ids=list(r.session.positions),
                   token=token,acknowledgements=sorted(r.missing_keys),actor=a).pk)
    finally: connections.close_all()
with ThreadPoolExecutor(max_workers=2) as pool: ids=list(pool.map(enqueue,range(2)))
assert ids[0]==ids[1] and GenerationRun.objects.count()==1
assert Job.objects.filter(kind='GENERATE').count()==1
"""
    subprocess.run([sys.executable, "-c", script], env=env, check=True, capture_output=True, timeout=90)
