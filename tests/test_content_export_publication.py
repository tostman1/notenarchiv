"""Real POSIX worker publishes authorized partial content with retained source pins."""

import hashlib
import json
import os

import pytest

from tests.test_archive_publication import Installation

pytestmark = pytest.mark.skipif(os.name != "posix", reason="Actual publication requires POSIX managed-root APIs")


def test_worker_publishes_content_without_whole_file_approval(tmp_path):
    installation = Installation(tmp_path / "content-installation")
    identities = installation.action("setup")
    installation.worker()
    raw = installation.root / "raw/correct.pdf"
    original = hashlib.sha256(raw.read_bytes()).hexdigest(), raw.stat().st_mtime_ns
    output = installation.code(
        "from apps.archive.models import ArchiveFile,ContentEdition,LogicalPage,LogicalPageRevision\n"
        "from apps.archive.content_services import propose_content,inspect_content,confirm_content\n"
        "from apps.archive.content_geometry_services import append_logical_page\n"
        "from apps.exports.content_export_services import report,token,authorize\n"
        "from django.contrib.auth import get_user_model\n"
        "f=ArchiveFile.objects.get(pk=data['file']); assert f.review_state!='CONFIRMED'\n"
        "actor=get_user_model().objects.get(pk=data['actor'])\n"
        "logical=LogicalPage.objects.create()\n"
        "page=LogicalPageRevision.objects.create(logical_page=logical,number=1,source_page=f.source_version.pages.first())\n"
        "edition=ContentEdition.objects.create(arrangement_id=data['arrangement'],part_id=data['parts'][0])\n"
        "proposal=propose_content(edition.pk,expected_number=0,inputs=[(page.pk,f.pk),(page.pk,f.pk)])\n"
        "inspection=inspect_content(proposal.pk,actor=actor,expected_fingerprint=proposal.fingerprint,visually_reviewed=True)\n"
        "confirm_content(inspection.pk,actor=actor)\n"
        "run=authorize([edition.pk],token(report([edition.pk]),actor),actor)\n"
        "append_logical_page(logical.pk,expected_number=1,source_page_id=page.source_page_id,orientation=90)\n"
        "print('CONTENT_RESULT='+json.dumps({'run':str(run.pk),'file':str(f.pk)}))",
        identities,
    )
    result = json.loads(
        next(line.removeprefix("CONTENT_RESULT=") for line in output.splitlines() if line.startswith("CONTENT_RESULT="))
    )
    installation.worker()
    installation.code(
        "from apps.exports.models import GenerationRun\n"
        "from apps.exports.generation import is_complete\n"
        "from apps.archive.models import ArchiveFile\n"
        "run=GenerationRun.objects.get(pk=data['run']); assert run.job.status=='SUCCEEDED',run.job.status\n"
        "assert is_complete(run) and run.artifacts.count()==1\n"
        "artifact=run.artifacts.get(); assert artifact.manifest['page_count']==2\n"
        "assert artifact.manifest['inputs']==run.snapshot.payload['content_editions']\n"
        "f=ArchiveFile.objects.get(pk=data['file']); assert f.review_state!='CONFIRMED'\n"
        "assert not f.assignments.exists()\n",
        result,
    )
    assert (hashlib.sha256(raw.read_bytes()).hexdigest(), raw.stat().st_mtime_ns) == original
