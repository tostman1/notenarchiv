"""Real SQLite migration, concurrent writers and independent interpreter restart."""

import json
import os
import subprocess
import sys


def test_archive_history_and_approval_survive_restart_and_competing_edits(tmp_path):
    environment = os.environ.copy()
    environment.update(
        DJANGO_SETTINGS_MODULE="config.settings",
        NOTENARCHIV_PROFILE="local",
        DEBUG_MODE="FALSE",
        NOTENARCHIV_LOCAL_ROOT=str(tmp_path / "synthetic-roots"),
        DATABASE_PATH=str(tmp_path / "synthetic.sqlite3"),
    )
    migrate = [sys.executable, "manage.py", "migrate", "--noinput"]
    subprocess.run(migrate, env=environment, check=True, capture_output=True, timeout=30)
    create = """
import django,json,sys,hashlib,threading
django.setup()
from concurrent.futures import ThreadPoolExecutor
from django.contrib.auth import get_user_model
from django.db import connections
from apps.archive import models as m,services as s
from apps.catalog.models import Work,Arrangement,InstrumentVariant,Part
from apps.catalog.services import save_record
from tests.pdf_fixtures import pdf
from tests.archive_fixtures import PAGE
from tests.test_archive_workflow import receipt,draft,confirm
data=pdf()
folder=m.SourceFolder.objects.create(relative_path='Synthetic')
version,_=s.observe_version(folder.pk,'Synthetic/scan.pdf',sha256=hashlib.sha256(data).hexdigest(),
    byte_size=len(data),pdf_state='VALID',page_info=[PAGE])
file=s.register_base(version.pk,'_Ungeprueft/synthetic.pdf')
file,_=receipt(file)
actor=get_user_model().objects.create_user('synthetic-persisted-reviewer')
work=save_record(Work(title='Synthetic persisted archive'))
arrangement=save_record(Arrangement(work=work))
variant=save_record(InstrumentVariant(name='Synthetic instrument'))
parts=[save_record(Part(instrument=variant,code=str(n))) for n in (1,2)]
file=confirm(file,draft(file,actor,arrangement,parts),actor)
old_revision=file.revision
barrier=threading.Barrier(2)
def edit():
    barrier.wait(timeout=10)
    try:
        s.create_proposal(file.pk,actor=actor.pk,arrangement_id=arrangement.pk,
            part_ids=[parts[0].pk],expected_revision=old_revision)
        return 'saved'
    except s.ArchiveConflict:
        return 'conflict'
    finally:
        connections.close_all()
with ThreadPoolExecutor(max_workers=2) as pool:
    results=list(pool.map(lambda _:edit(),range(2)))
assert sorted(results)==['conflict','saved'],results
sys.stdout.write(json.dumps({'file':str(file.pk),'version':str(version.pk),
    'approved':str(file.approved_proposal_id),'audits':m.AuditEvent.objects.count()}))
"""
    created = subprocess.run(
        [sys.executable, "-c", create], env=environment, check=True, capture_output=True, text=True, timeout=30
    )
    identities = json.loads(created.stdout)
    repeated = subprocess.run(migrate, env=environment, check=True, capture_output=True, text=True, timeout=30)
    assert "No migrations to apply" in repeated.stdout
    verify = """
import django,json,sys
django.setup()
from django.db import connection
from apps.archive import models as m
data=json.loads(sys.argv[1])
file=m.ArchiveFile.objects.usable().get(pk=data['file'])
assert str(file.source_version_id)==data['version']
assert str(file.approved_proposal_id)==data['approved']
assert file.current_proposal_id!=file.approved_proposal_id
assert m.ArchiveAssignment.objects.usable().count()==2
assert m.AuditEvent.objects.count()==data['audits']
assert file.proposals.count()==2 and file.operations.filter(state='APPLIED').count()==2
assert file.approved_proposal.inspections.count()==1
with connection.cursor() as cursor:
    assert cursor.execute('PRAGMA foreign_key_check').fetchall()==[]
    assert cursor.execute('PRAGMA integrity_check').fetchone()==('ok',)
sys.stdout.write('History, inspection, assignments and receipts persisted')
"""
    verified = subprocess.run(
        [sys.executable, "-c", verify, json.dumps(identities)],
        env=environment,
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert "receipts persisted" in verified.stdout
