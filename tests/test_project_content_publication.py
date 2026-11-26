"""Real worker consumes signed historical project content, never a newer region."""

import hashlib
import json
import os

import pytest

from tests.test_archive_publication import Installation

pytestmark = pytest.mark.skipif(os.name != "posix", reason="Actual publication requires POSIX managed-root APIs")


def test_authorized_project_worker_retains_content_and_source_history(tmp_path):
    installation = Installation(tmp_path / "project-content-installation")
    identities = installation.action("setup")
    installation.worker()
    raw = installation.root / "raw/correct.pdf"
    original = hashlib.sha256(raw.read_bytes()).hexdigest(), raw.stat().st_mtime_ns
    output = installation.code(
        "from uuid import uuid4\n"
        "from django.contrib.auth import get_user_model\n"
        "from apps.archive.models import ArchiveFile,ContentEdition,LogicalPage,LogicalPageRevision\n"
        "from apps.archive.content_services import propose_content,inspect_content,confirm_content\n"
        "from apps.archive.content_geometry_services import append_logical_page\n"
        "from apps.archive.content_preferences import set_content_preference\n"
        "from apps.catalog.models import Arrangement\n"
        "from apps.projects.models import Project,ProjectPosition,ProjectParticipant\n"
        "from apps.projects.preflight_services import build_report,report_token\n"
        "from apps.exports.snapshot_services import authorize\n"
        "f=ArchiveFile.objects.get(pk=data['file']); actor=get_user_model().objects.get(pk=data['actor'])\n"
        "logical=LogicalPage.objects.create()\n"
        "page=LogicalPageRevision.objects.create(logical_page=logical,number=1,source_page=f.source_version.pages.first())\n"
        "edition=ContentEdition.objects.create(arrangement_id=data['arrangement'],part_id=data['parts'][0])\n"
        "proposal=propose_content(edition.pk,expected_number=0,inputs=[(page.pk,f.pk),(page.pk,f.pk)])\n"
        "inspection=inspect_content(proposal.pk,actor=actor,expected_fingerprint=proposal.fingerprint,visually_reviewed=True)\n"
        "confirm_content(inspection.pk,actor=actor)\n"
        "arrangement=Arrangement.objects.get(pk=data['arrangement'])\n"
        "set_content_preference(arrangement.pk,edition.part_id,edition.pk,actor=actor,expected_revision=arrangement.revision)\n"
        "project=Project.objects.create(name='Synthetic content project',cover_enabled=False)\n"
        "position=ProjectPosition.objects.create(project=project,arrangement=arrangement,order=1)\n"
        "person=ProjectParticipant.objects.create(project=project,guest_id=uuid4(),"
        "display_name='Synthetic guest',default_part=edition.part)\n"
        "selection=dict(participant_ids=[person.pk],position_ids=[position.pk],include_content=True)\n"
        "report=build_report(project.pk,**selection); assert report.blocking==0,report.blocking\n"
        "run=authorize(project.pk,**selection,token=report_token(report,actor),acknowledgements=[],actor=actor,kind='FULL')\n"
        "assert run.snapshot.project_content_inputs.count()==1 and not run.snapshot.inputs.exists()\n"
        "append_logical_page(logical.pk,expected_number=1,source_page_id=page.source_page_id,orientation=90)\n"
        "print('PROJECT_RESULT='+json.dumps({'run':str(run.pk),'file':str(f.pk)}))",
        identities,
    )
    result = json.loads(
        next(line.removeprefix("PROJECT_RESULT=") for line in output.splitlines() if line.startswith("PROJECT_RESULT="))
    )
    installation.worker()
    installation.code(
        "from apps.exports.models import GenerationRun\n"
        "from apps.exports.generation import is_complete\n"
        "from apps.archive.models import ArchiveFile\n"
        "run=GenerationRun.objects.get(pk=data['run']); assert run.job.status=='SUCCEEDED',run.job.status\n"
        "assert is_complete(run) and run.artifacts.count()==1\n"
        "assert run.snapshot.payload['schema']==3\n"
        "assert run.snapshot.payload['cells'][0]['content']['inputs'][0]['orientation']==0\n"
        "assert run.artifacts.get().manifest['page_count']==2\n"
        "f=ArchiveFile.objects.get(pk=data['file'])\n"
        "assert f.review_state!='CONFIRMED' and not f.assignments.exists()\n",
        result,
    )
    assert (hashlib.sha256(raw.read_bytes()).hexdigest(), raw.stat().st_mtime_ns) == original
