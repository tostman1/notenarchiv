"""Independent file-SQLite writers and reopen of durable preference history."""

import os
import subprocess
import sys


def test_preference_race_and_reopen(tmp_path):
    environment = os.environ.copy()
    environment.update(
        DJANGO_SETTINGS_MODULE="config.settings",
        NOTENARCHIV_PROFILE="local",
        DEBUG_MODE="FALSE",
        NOTENARCHIV_LOCAL_ROOT=str(tmp_path / "roots"),
        DATABASE_PATH=str(tmp_path / "db" / "synthetic.sqlite3"),
    )
    subprocess.run(
        [sys.executable, "manage.py", "migrate", "--noinput"],
        env=environment,
        check=True,
        capture_output=True,
        timeout=30,
    )
    create = """
import django,hashlib,threading
django.setup()
from concurrent.futures import ThreadPoolExecutor
from django.contrib.auth import get_user_model
from django.db import connections
from apps.archive import models as m,services as s,edition_services as e
from apps.catalog import models as c
from tests.pdf_fixtures import pdf
from tests.archive_fixtures import PAGE
from tests.test_archive_workflow import receipt,draft,confirm
from config.env import env
actor=get_user_model().objects.create_user('synthetic-edition-persistence')
arr=c.Arrangement.objects.create(work=c.Work.objects.create(title='Synthetic editions'))
part=c.Part.objects.create(instrument=c.InstrumentVariant.objects.create(name='Synthetic'),code='2')
folder=m.SourceFolder.objects.create(relative_path='Synthetic')
choices=[]
for i in (1,2):
    data=pdf(text=bool(i%2))
    version,_=s.observe_version(folder.pk,f'Synthetic/{i}.pdf',sha256=hashlib.sha256(data).hexdigest(),byte_size=len(data),pdf_state='VALID',page_info=[PAGE])
    file,_=receipt(s.register_base(version.pk,f'_Ungeprueft/{i}.pdf'))
    file=confirm(file,draft(file,actor,arr,[part]),actor,path=f'Synthetic/{i}.pdf')
    target=env.curated_dir/file.relative_path
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(data)
    choices.append(file.assignments.get().pk)
barrier=threading.Barrier(2)
def save(choice):
    barrier.wait(timeout=10)
    try:
        e.set_preference(arr.pk,part.pk,choice,actor=actor.pk,expected_revision=1)
        return 'saved'
    except s.ArchiveConflict:
        return 'conflict'
    finally:
        connections.close_all()
with ThreadPoolExecutor(max_workers=2) as pool:
    results=list(pool.map(save,choices))
assert sorted(results)==['conflict','saved'],results
assert m.PreferredEdition.objects.count()==1
assert m.EditionPreferenceChange.objects.count()==1
"""
    subprocess.run([sys.executable, "-c", create], env=environment, check=True, capture_output=True, timeout=60)
    verify = """
import django
django.setup()
from django.db import connection
from apps.archive import models as m,edition_services as e
pref=m.PreferredEdition.objects.get()
assert pref.changes.get().selected_id==pref.assignment_id
result=e.resolve(pref.arrangement_id,pref.part_id)
assert result.origin=='ARCHIVE' and result.assignment.pk==pref.assignment_id
assert m.ArchiveFile.objects.usable().count()==2
with connection.cursor() as cursor:
    assert cursor.execute('PRAGMA foreign_key_check').fetchall()==[]
    assert cursor.execute('PRAGMA integrity_check').fetchone()==('ok',)
"""
    subprocess.run([sys.executable, "-c", verify], env=environment, check=True, capture_output=True, timeout=30)
