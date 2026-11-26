"""Real synthetic CLEAN reconstruction using an independent Linux worker."""

import os

import pytest

from tests.test_archive_publication import Installation

pytestmark = pytest.mark.skipif(os.name != "posix", reason="CLEAN restoration requires the POSIX writable backend")


def _queue(installation, identities):
    return installation.run("manage.py", "restore_clean_copy", identities["file"]).stdout.strip().splitlines()[-1]


def _prepared(installation, *, confirmed):
    identities = installation.action("setup")
    installation.worker()
    copied = installation.action("check-copy", identities)
    history = None
    if confirmed:
        identities = installation.action("review", identities)
        installation.worker()
        history = installation.root / "clean" / copied["path"]
        copied = installation.action("check-approved", identities)
    target = installation.root / "clean" / copied["path"]
    revision, receipt = installation.code(
        "from apps.archive.models import ArchiveFile\nfile=ArchiveFile.objects.get(pk=data['file'])\n"
        "print(file.revision,file.publication_operation_id)\n",
        identities,
    ).split()
    identities.update(revision=revision, receipt=receipt, review="CONFIRMED" if confirmed else "PENDING")
    expected = target.read_bytes()
    target.unlink()
    return identities, target, expected, history


def _assert_restored(installation, identities, target, expected, job):
    installation.code(
        "from apps.archive.models import ArchiveFile\nfrom apps.jobs.models import Job\n"
        "from apps.archive.publication import verified_bytes\n"
        "file=ArchiveFile.objects.get(pk=data['file']); job=Job.objects.get(pk=data['job'])\n"
        "assert job.status=='SUCCEEDED',(job.status,job.error_code)\n"
        "assert file.publication_state=='AVAILABLE' and file.review_state==data['review']\n"
        "assert str(file.revision)==data['revision'] and str(file.publication_operation_id)==data['receipt']\n"
        "assert job.operations.get().state=='APPLIED' and not job.file_operations.exists()\n"
        "assert verified_bytes(file.pk)\n",
        {**identities, "job": job},
    )
    assert target.read_bytes() == expected and target.stat().st_nlink == 1
    assert not list((installation.root / "clean" / ".staging").rglob("*.pdf"))


@pytest.mark.parametrize("source", ["raw", "historical-clean"])
def test_restore_only_missing_copy_with_exact_retained_source(tmp_path, source):
    installation = Installation(tmp_path / "restore")
    confirmed = source == "historical-clean"
    identities, target, expected, history = _prepared(installation, confirmed=confirmed)
    raw = installation.root / "raw" / "correct.pdf"
    if confirmed:
        raw.write_bytes(b"Synthetic changed RAW")
    before = raw.read_bytes()
    job = _queue(installation, identities)
    assert not target.exists()
    installation.worker()
    _assert_restored(installation, identities, target, expected, job)
    assert raw.read_bytes() == before
    original = history if confirmed else raw
    assert original.read_bytes() == expected and target.stat().st_ino != original.stat().st_ino


def test_restore_preserves_target_if_it_appears_before_worker_runs(tmp_path):
    installation = Installation(tmp_path / "restore")
    identities, target, _, _ = _prepared(installation, confirmed=False)
    job = _queue(installation, identities)
    conflicting = b"Synthetic unrelated target"
    target.write_bytes(conflicting)
    installation.worker()
    installation.code(
        "from apps.jobs.models import Job\njob=Job.objects.get(pk=data['job'])\n"
        "assert job.status in {'FAILED','REVIEW_REQUIRED'},(job.status,job.error_code)\n"
        "assert not job.operations.filter(state='APPLIED').exists()\n",
        {"job": job},
    )
    assert target.read_bytes() == conflicting


def test_restore_does_not_use_changed_raw(tmp_path):
    installation = Installation(tmp_path / "restore")
    identities, target, _, _ = _prepared(installation, confirmed=False)
    job = _queue(installation, identities)
    raw = installation.root / "raw" / "correct.pdf"
    changed = b"Synthetic changed input"
    raw.write_bytes(changed)
    installation.worker()
    installation.code(
        "from apps.jobs.models import Job\njob=Job.objects.get(pk=data['job'])\n"
        "assert job.status in {'FAILED','REVIEW_REQUIRED'},(job.status,job.error_code)\n"
        "assert not job.operations.filter(state='APPLIED').exists()\n",
        {"job": job},
    )
    assert not target.exists() and raw.read_bytes() == changed


@pytest.mark.parametrize("phase", ["link", "acknowledgement", "lost-proof"])
def test_restore_reconciles_process_death_without_changing_receipt(tmp_path, phase):
    installation = Installation(tmp_path / "restore")
    identities, target, expected, _ = _prepared(installation, confirmed=False)
    job = _queue(installation, identities)
    module = "apps.jobs.services.lifecycle" if phase == "acknowledgement" else "core.files"
    script = f"""
import django, os
django.setup()
from django.core.management import call_command
import {module} as implementation
original = implementation.publish
def wrapped(*args, **kwargs):
    original(*args, **kwargs)
    os._exit(39)
implementation.publish = wrapped
call_command('run_worker', once=True)
"""
    result = installation.run("-c", script, check=False)
    assert result.returncode == 39, result.stdout + result.stderr
    assert target.read_bytes() == expected
    if phase == "lost-proof":
        (proof,) = (installation.root / "clean" / ".staging").rglob("*.pdf")
        proof.unlink()
        installation.worker()
        installation.code(
            "from apps.archive.models import ArchiveFile\nfrom apps.jobs.models import Job\n"
            "file=ArchiveFile.objects.get(pk=data['file']); job=Job.objects.get(pk=data['job'])\n"
            "assert job.status=='REVIEW_REQUIRED',(job.status,job.error_code)\n"
            "assert job.operations.get().state=='REVIEW_REQUIRED'\n"
            "assert file.publication_state=='MISSING' and str(file.publication_operation_id)==data['receipt']\n",
            {**identities, "job": job},
        )
        assert target.read_bytes() == expected
        return
    installation.recover({"job": job})
    _assert_restored(installation, identities, target, expected, job)
