"""Synthetic complete booklet crosses authorization and the actual durable worker."""

import hashlib
import json
import os
import subprocess
import sys

import pytest

from tests.test_archive_publication import Installation

pytestmark = pytest.mark.skipif(os.name != "posix", reason="Actual publication requires POSIX managed roots")


class BookletInstallation(Installation):
    """Keep full-booklet acceptance bounded without changing application deadlines."""

    def run(self, *arguments, check=True):
        return subprocess.run(
            [sys.executable, *arguments],
            env=self.environment,
            check=check,
            capture_output=True,
            text=True,
            timeout=180,
        )


def test_all_125_confirmed_booklet_editions_publish_with_retained_history(tmp_path):
    installation = BookletInstallation(tmp_path / "full-booklet")
    identities = installation.action("setup")
    installation.worker()
    raw = installation.root / "raw/correct.pdf"
    original = hashlib.sha256(raw.read_bytes()).hexdigest(), raw.stat().st_mtime_ns
    output = installation.code(
        "from apps.archive.models import ArchiveFile,ContentEdition,LogicalPage,LogicalPageRevision\n"
        "from apps.archive.content_services import propose_content,inspect_content,confirm_content\n"
        "from apps.archive.content_geometry_services import append_logical_page\n"
        "from apps.catalog.models import Work,Arrangement,Collection\n"
        "from apps.catalog.collection_services import add_membership\n"
        "from apps.exports.content_export_services import report,token,authorize\n"
        "from django.contrib.auth import get_user_model\n"
        "f=ArchiveFile.objects.get(pk=data['file'])\n"
        "actor=get_user_model().objects.get(pk=data['actor'])\n"
        "logical=LogicalPage.objects.create()\n"
        "page=LogicalPageRevision.objects.create(logical_page=logical,number=1,"
        "source_page=f.source_version.pages.first())\n"
        "collection=Collection.objects.create(title='Synthetic 125-piece booklet')\n"
        "editions=[]\n"
        "for number in range(125):\n"
        "    work=Work.objects.create(title='Synthetic repeated title')\n"
        "    add_membership(collection.pk,work.pk,position=number,original_song_number=str(number+1))\n"
        "    arrangement=Arrangement.objects.create(work=work)\n"
        "    edition=ContentEdition.objects.create(arrangement=arrangement,part_id=data['parts'][0])\n"
        "    proposal=propose_content(edition.pk,expected_number=0,inputs=[(page.pk,f.pk)])\n"
        "    inspected=inspect_content(proposal.pk,actor=actor,"
        "expected_fingerprint=proposal.fingerprint,visually_reviewed=True)\n"
        "    confirm_content(inspected.pk,actor=actor)\n"
        "    editions.append(edition.pk)\n"
        "entries=report(editions); assert len(entries)==125\n"
        "run=authorize(editions,token(entries,actor),actor)\n"
        "assert run.snapshot.content_inputs.count()==125\n"
        "assert len({x['inputs'][0]['occurrence_id'] for x in "
        "run.snapshot.payload['content_editions']})==125\n"
        "append_logical_page(logical.pk,expected_number=1,source_page_id=page.source_page_id,orientation=90)\n"
        "print('BOOKLET_RESULT='+json.dumps({'run':str(run.pk),'file':str(f.pk)}))",
        identities,
    )
    result = json.loads(
        next(line.removeprefix("BOOKLET_RESULT=") for line in output.splitlines() if line.startswith("BOOKLET_RESULT="))
    )
    installation.worker()
    installation.code(
        "from apps.exports.models import GenerationRun\n"
        "from apps.exports.generation import is_complete\n"
        "from apps.archive.models import ArchiveFile\n"
        "run=GenerationRun.objects.get(pk=data['run'])\n"
        "assert run.job.status=='SUCCEEDED',run.job.status\n"
        "assert is_complete(run) and run.artifacts.count()==1\n"
        "artifact=run.artifacts.get(); assert artifact.manifest['page_count']==125\n"
        "assert artifact.manifest['inputs']==run.snapshot.payload['content_editions']\n"
        "assert all(x['inputs'][0]['orientation']==0 for x in artifact.manifest['inputs'])\n"
        "f=ArchiveFile.objects.get(pk=data['file'])\n"
        "assert f.review_state!='CONFIRMED' and not f.assignments.exists()\n"
        "assert ArchiveFile.objects.filter(source_version=f.source_version,kind='BASE').count()==1\n",
        result,
    )
    assert (hashlib.sha256(raw.read_bytes()).hexdigest(), raw.stat().st_mtime_ns) == original
