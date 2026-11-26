"""Neutral compound CLEAN publication uses the unchanged durable POSIX worker."""

import hashlib
import json
import os

import pytest

from tests.test_archive_publication import Installation

pytestmark = pytest.mark.skipif(os.name != "posix", reason="Actual publication requires POSIX managed-root APIs")


def test_neutral_compound_copy_is_one_exact_unapproved_source(tmp_path):
    installation = Installation(tmp_path / "compound-installation")
    output = installation.code(
        "from tests.publication_scenario import setup\n"
        "data=setup(compound_title='125 Stücke – Testsammlung')\n"
        "print('COMPOUND_RESULT='+json.dumps(data))",
        {},
    )
    identities = json.loads(
        next(
            line.removeprefix("COMPOUND_RESULT=") for line in output.splitlines() if line.startswith("COMPOUND_RESULT=")
        )
    )
    raw = installation.root / "raw/correct.pdf"
    before = hashlib.sha256(raw.read_bytes()).hexdigest(), raw.stat().st_mtime_ns
    installation.worker()
    installation.code(
        "from apps.archive.models import ArchiveFile\n"
        "from apps.archive.publication import queue_compound_copy\n"
        "from apps.archive.library_services import verify_publication\n"
        "f=ArchiveFile.objects.get(pk=data['file']); assert verify_publication(f)\n"
        "from core.naming import component\n"
        "assert f.relative_path.startswith('Sammlungen/'+component('125 Stücke – Testsammlung')), f.relative_path\n"
        "assert f.review_state!='CONFIRMED' and not f.assignments.exists()\n"
        "assert f.sha256==f.source_version.sha256 and f.byte_size==f.source_version.byte_size\n"
        "old=(f.relative_path,f.revision,f.publication_operation_id)\n"
        "again,job=queue_compound_copy(data['version'],title='Andere Metadaten')\n"
        "assert again.pk==f.pk and (again.relative_path,again.revision,again.publication_operation_id)==old\n"
        "assert ArchiveFile.objects.filter(source_version=f.source_version,kind='BASE').count()==1\n",
        identities,
    )
    assert before == (hashlib.sha256(raw.read_bytes()).hexdigest(), raw.stat().st_mtime_ns)
