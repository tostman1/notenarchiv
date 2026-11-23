"""Independent SQLite reopen for contents and historical exact excerpt pins."""

import os
import subprocess
import sys


def test_contents_and_historical_selection_survive_database_restart(tmp_path):
    from tests.test_generation_snapshot_persistence import test_authorization_survives_independent_process_reopen

    test_authorization_survives_independent_process_reopen(tmp_path)
    env = os.environ.copy()
    env.update(
        DJANGO_SETTINGS_MODULE="config.settings",
        NOTENARCHIV_PROFILE="local",
        DEBUG_MODE="FALSE",
        NOTENARCHIV_LOCAL_ROOT=str(tmp_path / "roots"),
        DATABASE_PATH=str(tmp_path / "data/synthetic.sqlite3"),
    )
    script = """
import django
django.setup()
from apps.exports.models import GenerationRun
from apps.exports.selection_services import contents_report,historical_report,selection_token,authorize_selection
from django.contrib.auth import get_user_model
old=GenerationRun.objects.get();a=get_user_model().objects.get(username='synthetic-resolver-persist')
person=old.snapshot.participants.get();position=old.snapshot.positions.get()
reports=(contents_report(old.snapshot.project_id),
         historical_report(old.snapshot_id,[person.participant_id],[position.position_id]))
for report in reports:
    run=authorize_selection(report,selection_token(report,a),report.missing,a)
    assert run.job.status=='QUEUED'
"""
    subprocess.run([sys.executable, "-c", script], env=env, check=True, capture_output=True, timeout=60)
    reopen = """
import django
django.setup()
from apps.exports.models import GenerationRun
from apps.exports.snapshot_services import load_pinned_inputs
assert GenerationRun.objects.count()==3
for run in GenerationRun.objects.all():
    s,pins=load_pinned_inputs(run.snapshot_id)
    if s.kind=='CONTENTS': assert not pins and not s.participants.exists()
    if s.source_snapshot_id: assert s.kind=='EXCERPT' and len(pins)==1 and s.project_revision==1
"""
    subprocess.run([sys.executable, "-c", reopen], env=env, check=True, capture_output=True, timeout=30)
