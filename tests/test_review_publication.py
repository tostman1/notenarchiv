"""Individual HTTP review queues real POSIX publication and crash recovery."""

import json
import os

import pytest

from tests.test_archive_publication import Installation

pytestmark = pytest.mark.skipif(os.name != "posix", reason="Real safe publication requires POSIX")


def test_http_review_then_actual_worker_death_recovers_confirmed_assignment(tmp_path):
    installation = Installation(tmp_path / "synthetic-http-review")
    identities = installation.action("setup")
    installation.worker()
    code = """
from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.archive import models as m
from apps.jobs.models import Job
file=m.ArchiveFile.objects.get(pk=data['file'])
client=Client(HTTP_HOST='localhost'); client.force_login(get_user_model().objects.get(pk=data['actor']))
url=reverse('archive_review_detail',args=[file.pk])
assert client.get(url).status_code==200
assert m.ReviewInspection.objects.count()==0
def values(action, **extra):
    file.refresh_from_db()
    return {'action':action,'expected_revision':file.revision,'source_version':str(file.source_version_id),
            'sha256':file.sha256,'proposal':str(file.current_proposal_id) if file.current_proposal_id else '',**extra}
from apps.catalog.models import Part
instrument=str(Part.objects.get(pk=data['parts'][0]).instrument_id)
correction=values('save',arrangement=data['arrangement'],instruments=[instrument],parts=data['parts'])
assert client.post(url,correction).status_code==302
assert client.post(url,values('approve',explicit='on')).status_code==409
assert client.post(url,values('inspect',explicit='on')).status_code==302
assert client.post(url,values('approve',explicit='on')).status_code==302
file.refresh_from_db()
assert file.review_state=='APPROVAL_REQUESTED' and not m.ArchiveFile.objects.usable().exists()
job=Job.objects.get(status='QUEUED')
data.update(job=str(job.pk),proposal=str(file.current_proposal_id))
print('REVIEW_RESULT='+json.dumps(data))
"""
    output = installation.code(code, identities)
    identities = json.loads(
        next(line.removeprefix("REVIEW_RESULT=") for line in output.splitlines() if line.startswith("REVIEW_RESULT="))
    )
    installation.action("crash-after-link", expected=23)
    installation.recover(identities)
    installation.action("check-approved", identities)
    installation.code(
        "from apps.archive.models import AuditEvent\n"
        "assert AuditEvent.objects.filter(event='INSPECTED').count()==1\n"
        "assert AuditEvent.objects.filter(event='CONFIRMED').count()==1",
        identities,
    )


def test_nested_approval_waits_for_independent_sqlite_writer_without_reader_upgrade(tmp_path):
    installation = Installation(tmp_path / "synthetic-concurrent-review")
    ids = installation.action("setup")
    installation.worker()
    code = """
import sqlite3,threading
from config.env import env
from apps.archive import models as m,services as s,publication as p
file=m.ArchiveFile.objects.get(pk=data['file'])
proposal=s.create_proposal(file.pk,actor=data['actor'],arrangement_id=data['arrangement'],
    part_ids=data['parts'],expected_revision=file.revision)
file.refresh_from_db()
s.record_inspection(proposal.pk,actor=data['actor'],inspected_sha256=file.sha256,
    explicit=True,expected_revision=file.revision)
file.refresh_from_db()
held,finish=threading.Event(),threading.Event()
errors=[]
def writer():
    try:
        with sqlite3.connect(env.database_path,timeout=5) as database:
            database.execute('BEGIN IMMEDIATE')
            database.execute('UPDATE jobs_workerlease SET generation=generation WHERE id=1')
            held.set()
            assert finish.wait(5)
    except Exception as error:
        errors.append(error)
thread=threading.Thread(target=writer);thread.start();assert held.wait(5)
original=p.choose_target
timer=None
def chosen(*args,**kwargs):
    global timer
    result=original(*args,**kwargs)
    timer=threading.Timer(0.3,finish.set);timer.start()
    return result
p.choose_target=chosen
try:
    job=p.queue_canonical(proposal.pk,actor=data['actor'],expected_revision=file.revision)
    assert job.status=='QUEUED'
finally:
    finish.set();thread.join(10)
    if timer: timer.join(10)
assert not thread.is_alive() and not errors
file.refresh_from_db();assert file.review_state=='APPROVAL_REQUESTED'
"""
    installation.code(code, ids)
    installation.worker()
    installation.code(
        "from apps.archive.models import ArchiveFile\n"
        "assert ArchiveFile.objects.get(pk=data['file']).review_state=='CONFIRMED'",
        ids,
    )
