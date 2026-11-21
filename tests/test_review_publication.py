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
client=Client(); client.force_login(get_user_model().objects.get(pk=data['actor']))
url=reverse('archive_review_detail',args=[file.pk])
assert client.get(url).status_code==200
assert m.ReviewInspection.objects.count()==0
def values(action, **extra):
    file.refresh_from_db()
    return {'action':action,'expected_revision':file.revision,'source_version':str(file.source_version_id),
            'sha256':file.sha256,'proposal':str(file.current_proposal_id) if file.current_proposal_id else '',**extra}
from apps.catalog.models import Part
instrument=str(Part.objects.get(pk=data['parts'][0]).instrument_id)
assert client.post(url,values('save',arrangement=data['arrangement'],instruments=[instrument],parts=data['parts'])).status_code==302
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
