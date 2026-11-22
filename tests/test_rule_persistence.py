"""Global rule revision serialization and project preference restore across processes."""

import os
import subprocess
import sys


def test_global_rule_race_and_reopen(tmp_path):
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
from apps.catalog.models import InstrumentVariant,Part
from apps.projects import models as m,rule_services as s,services as p
actor=get_user_model().objects.create_user('synthetic-rule-persist')
variant=InstrumentVariant.objects.create(name='Synthetic rule')
parts=[Part.objects.create(instrument=variant,code=str(n)) for n in (1,2,3)]
barrier=threading.Barrier(2)
def save(target):
    barrier.wait(timeout=10)
    try:
        s.save_replacement(desired_part_id=parts[0].pk,replacement_part_id=target.pk,
            actor=actor.pk,expected_revision=1)
        return 'saved'
    except p.ProjectConflict:
        return 'conflict'
    finally:
        connections.close_all()
with ThreadPoolExecutor(max_workers=2) as pool:
    results=list(pool.map(save,parts[1:]))
assert sorted(results)==['conflict','saved'],results
assert m.GlobalRuleState.objects.get(pk=1).revision==2
assert m.GlobalReplacementRule.objects.count()==1 and m.RuleChange.objects.count()==1
"""
    subprocess.run([sys.executable, "-c", code], env=env, check=True, capture_output=True, timeout=40)
    reopen = """
import django
django.setup()
from django.db import connection
from apps.projects import models as m,rule_services as s
rule=m.GlobalReplacementRule.objects.get()
assert m.GlobalRuleState.objects.get(pk=1).revision==2
assert s.replacement_choice(None,None,rule.desired_part_id).part.pk==rule.replacement_part_id
assert m.RuleChange.objects.get().selected_part_id==rule.replacement_part_id
with connection.cursor() as cursor:
    assert cursor.execute('PRAGMA foreign_key_check').fetchall()==[]
    assert cursor.execute('PRAGMA integrity_check').fetchone()==('ok',)
"""
    subprocess.run([sys.executable, "-c", reopen], env=env, check=True, capture_output=True, timeout=30)
