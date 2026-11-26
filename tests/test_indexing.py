"""Synthetic indexing API contracts and real independent Linux worker acceptance."""

import hashlib
import json
import os

import pytest

from apps.archive import models as m
from apps.archive.indexing import queue_index
from apps.archive.services import ArchiveConflict
from apps.jobs.models import Job
from tests.publication_scenario import synthetic_pdf
from tests.test_archive_publication import Installation


def test_copy_progress_does_not_regress_global_index_progress():
    from types import SimpleNamespace

    from apps.archive.indexing import CopyContext

    calls = []
    context = SimpleNamespace(checkpoint=lambda progress=None: calls.append(progress), using="default")
    copy = CopyContext(context, SimpleNamespace(pk="synthetic-operation"))
    for progress in (10, 80, None):
        copy.checkpoint(progress)
    assert calls == [None, None, None] and copy.using == "default"


@pytest.mark.django_db
def test_selection_is_canonical_durable_and_overlapping_jobs_are_not_duplicated():
    job = queue_index("selected")
    assert job.kind == "INDEX_SCAN" and job.index_scan.selected_path == "selected"
    assert queue_index("selected").pk == job.pk
    with pytest.raises(ArchiveConflict):
        queue_index("selected/nested")
    with pytest.raises(ArchiveConflict):
        queue_index()
    assert queue_index("independent").pk != job.pk
    for path in ("../escape", "/absolute", "bad\\path", "a//b"):
        with pytest.raises(ValueError):
            queue_index(path)
    assert m.IndexScan.objects.count() == 2


@pytest.mark.django_db
def test_unknown_payloads_are_rejected_and_uncertain_scans_block_replacement():
    from apps.jobs.services import queue

    with pytest.raises(queue.InvalidPayload):
        queue.enqueue("INDEX_SCAN", {"path": "/raw"})
    job = queue_index("selected")
    Job.objects.filter(pk=job.pk).update(status="REVIEW_REQUIRED")
    assert queue_index("selected").pk == job.pk


def raw_snapshot(root):
    result = {}
    for path in sorted(root.rglob("*")):
        info = path.lstat()
        result[str(path.relative_to(root))] = (
            info.st_mode,
            info.st_size,
            info.st_mtime_ns,
            info.st_ctime_ns,
            hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() and not path.is_symlink() else None,
        )
    return result


@pytest.fixture
def indexed_installation(tmp_path):
    if os.name != "posix":
        pytest.skip("Actual indexing requires POSIX no-follow/dir-fd APIs")
    return Installation(tmp_path / "synthetic-index")


def enqueue(installation, folder=""):
    result = installation.run("manage.py", "index_archive", "--folder", folder)
    return result.stdout.strip().splitlines()[-1]


def query(installation, code, job):
    return installation.code(code, {"job": job})


def test_complete_new_import_verifies_copies_and_raw_is_identical(indexed_installation):
    installation = indexed_installation
    root = installation.root
    selected = root / "raw" / "Selected"
    selected.mkdir()
    (selected / "unknown.PDF").write_bytes(synthetic_pdf())
    (selected / "readme.txt").write_text("Synthetic non-music file", encoding="utf-8")
    before = raw_snapshot(root / "raw")
    job = enqueue(installation, "Selected")
    installation.worker()
    query(
        installation,
        "from apps.archive import models as m\nfrom apps.archive.publication import verified_bytes\n"
        "from apps.jobs.models import Job\njob=Job.objects.get(pk=data['job'])\n"
        "assert job.status=='SUCCEEDED',(job.status,job.error_code)\n"
        "scan=job.index_scan; assert scan.completed and scan.entries.count()==2\n"
        "file=m.ArchiveFile.objects.get(); assert file.candidate_state=='UNKNOWN'\n"
        "assert file.review_state=='PENDING' and file.arrangement_id is None\n"
        "assert file.source_version.pdf_state=='VALID' and file.source_version.page_info\n"
        "assert verified_bytes(file.pk) and file.publication_state=='AVAILABLE'\n"
        "assert not m.ArchiveFile.objects.usable().exists() and not file.assignments.exists()\n"
        "assert not m.SourceVersion.objects.filter(source_file__relative_path='correct.pdf').exists()\n",
        job,
    )
    copies = list((root / "clean" / "_Ungeprueft").rglob("*.pdf"))
    assert len(copies) == 1 and copies[0].read_bytes() == synthetic_pdf()
    assert copies[0].stat().st_ino != (selected / "unknown.PDF").stat().st_ino
    marker = json.loads((root / "status" / "Selected" / "INDEXSTATUS.json").read_bytes())
    assert marker["index_state"] == "INDEXED" and marker["indexed"] == 1 and marker["failed"] == 0
    assert (root / "status" / "Selected" / "_INDIZIERT_BITTE_PRUEFEN.txt").is_file()
    assert raw_snapshot(root / "raw") == before
    assert not list((root / "raw").rglob("INDEXSTATUS.json"))


@pytest.mark.parametrize("state", ["MISSING", "CORRUPT"])
def test_index_records_unavailable_clean_without_replacing_publication(indexed_installation, state):
    installation = indexed_installation
    identities = installation.action("setup")
    installation.worker()
    identities = installation.action("review", identities)
    installation.worker()
    approved = installation.action("check-approved", identities)
    clean = installation.root / "clean"
    copy = clean / approved["path"]
    (historical,) = set(clean.rglob("*.pdf")) - {copy}
    original = copy.read_bytes()
    revision, receipt = installation.code(
        "from apps.archive import models as m\nfile=m.ArchiveFile.objects.get()\n"
        "print(file.revision,file.publication_operation_id)\n",
        {},
    ).split()
    if state == "MISSING":
        copy.unlink()
    else:
        replacement = installation.root / "synthetic-corrupt-copy"
        corrupted = original[:-1] + bytes([original[-1] ^ 1])
        replacement.write_bytes(corrupted)
        replacement.replace(copy)

    for _ in range(2):
        job = enqueue(installation)
        installation.worker()
        installation.code(
            "from apps.archive import models as m\nfrom apps.jobs.models import Job\n"
            "file=m.ArchiveFile.objects.get()\n"
            "assert file.publication_state==data['state'] and file.review_state=='CONFIRMED'\n"
            "assert not m.ArchiveFile.objects.usable().exists()\n"
            "assert file.operations.count()==2 and file.publication_operation.kind=='CANONICALIZE'\n"
            "assert file.publication_operation.state=='APPLIED'\n"
            "assert str(file.revision)==data['revision'] and str(file.publication_operation_id)==data['receipt']\n"
            "entry=Job.objects.get(pk=data['job']).index_scan.entries.get()\n"
            "assert entry.state=='FAILED' and entry.error_code=='CLEAN_'+data['state']\n",
            {"job": job, "state": state, "revision": revision, "receipt": receipt},
        )
    if state == "MISSING":
        assert list(clean.rglob("*.pdf")) == [historical]
    else:
        assert set(clean.rglob("*.pdf")) == {copy, historical} and copy.read_bytes() == corrupted
    assert historical.read_bytes() == original

    restored = installation.root / "synthetic-restored-copy"
    restored.write_bytes(original)
    restored.chmod(0o440)
    restored.replace(copy)
    job = enqueue(installation)
    installation.worker()
    installation.code(
        "from apps.archive import models as m\nfrom apps.jobs.models import Job\n"
        "file=m.ArchiveFile.objects.get()\n"
        "assert file.publication_state=='AVAILABLE' and file.review_state=='CONFIRMED'\n"
        "assert m.ArchiveFile.objects.usable().get()==file\n"
        "assert file.operations.count()==2 and file.publication_operation.kind=='CANONICALIZE'\n"
        "assert file.publication_operation.state=='APPLIED'\n"
        "assert str(file.revision)==data['revision'] and str(file.publication_operation_id)==data['receipt']\n"
        "assert Job.objects.get(pk=data['job']).index_scan.entries.get().state=='COPIED'\n",
        {"job": job, "revision": revision, "receipt": receipt},
    )
    assert set(clean.rglob("*.pdf")) == {copy, historical}
    assert copy.read_bytes() == historical.read_bytes() == original


def test_changed_missing_corrupt_and_unchanged_sources_preserve_history(indexed_installation):
    installation = indexed_installation
    root = installation.root
    job = enqueue(installation)
    installation.worker()
    first = list((root / "clean" / "_Ungeprueft").rglob("*.pdf"))[0]
    original = first.read_bytes()
    # Actual synthetic source-owner changes, not application mutations.
    raw = root / "raw" / "correct.pdf"
    raw.write_bytes(original + b"\n% Synthetic changed version\n")
    (root / "raw" / "broken.pdf").write_bytes(b"not a PDF")
    before = raw_snapshot(root / "raw")
    second = enqueue(installation)
    installation.worker()
    query(
        installation,
        "from apps.archive import models as m\nfrom apps.jobs.models import Job\n"
        "job=Job.objects.get(pk=data['job']); assert job.status=='SUCCEEDED',(job.status,job.error_code)\n"
        "assert m.SourceVersion.objects.filter(source_file__relative_path='correct.pdf').count()==2\n"
        "assert m.SourceFile.objects.get(relative_path='correct.pdf').presence=='CHANGED'\n"
        "assert m.SourceVersion.objects.get(source_file__relative_path='broken.pdf').pdf_state=='INVALID'\n"
        "assert m.ArchiveFile.objects.count()==2 and not m.ArchiveFile.objects.usable().exists()\n"
        "assert m.SourceFolder.objects.get(relative_path='').index_state=='PARTIAL_FAILURE'\n",
        second,
    )
    assert first.read_bytes() == original and raw_snapshot(root / "raw") == before
    raw.unlink()
    third = enqueue(installation)
    installation.worker()
    query(
        installation,
        "from apps.archive import models as m\n"
        "assert m.SourceFile.objects.get(relative_path='correct.pdf').presence=='MISSING'\n"
        "assert m.ArchiveFile.objects.count()==2\n",
        third,
    )
    assert first.read_bytes() == original
    assert json.loads((root / "status" / "INDEXSTATUS.json").read_bytes())["missing"] == 1
    assert job != second != third


def test_repeated_hash_import_is_idempotent_and_detects_same_size_mtime_changes(indexed_installation):
    installation = indexed_installation
    enqueue(installation)
    installation.worker()
    job = enqueue(installation)
    installation.worker()
    query(
        installation,
        "from apps.archive import models as m\n"
        "assert m.SourceVersion.objects.count()==1 and m.ArchiveFile.objects.count()==1\n"
        "assert m.FileOperation.objects.count()==1 and m.RecognitionCandidate.objects.count()==1\n",
        job,
    )
    raw = installation.root / "raw" / "correct.pdf"
    before = raw.stat()
    data = raw.read_bytes().replace(b"595.276", b"596.276")
    assert len(data) == before.st_size
    raw.write_bytes(data)
    os.utime(raw, ns=(before.st_atime_ns, before.st_mtime_ns))
    changed = enqueue(installation)
    installation.worker()
    query(
        installation,
        "from apps.archive import models as m\n"
        "assert m.SourceVersion.objects.count()==2 and m.ArchiveFile.objects.count()==2\n",
        changed,
    )


def test_symlink_and_unknown_status_conflicts_are_never_followed_or_overwritten(indexed_installation):
    installation = indexed_installation
    root = installation.root
    outside = root / "outside.pdf"
    outside.write_bytes(synthetic_pdf())
    (root / "raw" / "link.pdf").symlink_to(outside)
    before = raw_snapshot(root / "raw")
    (root / "status" / "INDEXSTATUS.json").write_bytes(b"Synthetic unrelated history")
    job = enqueue(installation)
    installation.worker()
    query(
        installation,
        "from apps.archive import models as m\nfrom apps.jobs.models import Job\n"
        "assert Job.objects.get(pk=data['job']).status=='FAILED'\n"
        "assert m.IndexEntry.objects.get(relative_path='link.pdf').error_code=='UNSAFE_FILE'\n"
        "assert not m.SourceVersion.objects.filter(source_file__relative_path='link.pdf').exists()\n",
        job,
    )
    assert (root / "status" / "INDEXSTATUS.json").read_bytes() == b"Synthetic unrelated history"
    assert raw_snapshot(root / "raw") == before and outside.read_bytes() == synthetic_pdf()


@pytest.mark.parametrize("crash", ["copy", "status", "inventory"])
def test_real_process_death_resumes_indexing_without_duplicate_copies(indexed_installation, crash):
    installation = indexed_installation
    job = enqueue(installation)
    script = """
import django, os
django.setup()
from django.core.management import call_command
from apps.archive import indexing, status
from core import files
mode = MODE
if mode == 'copy':
    original = files.publish
    def die(*args, **kwargs):
        original(*args, **kwargs)
        os._exit(71)
    files.publish = die
elif mode == 'status':
    from apps.jobs.services.worker import JobContext
    original = JobContext.publish
    def die(self, key, payload, apply):
        if key.startswith('index-status:'):
            def effect():
                result = apply()
                os._exit(71)
                return result
            return original(self, key, payload, effect)
        return original(self, key, payload, apply)
    JobContext.publish = die
else:
    original = indexing._record_inventory
    def die(*args, **kwargs):
        original(*args, **kwargs)
        os._exit(71)
    indexing._record_inventory = die
call_command('run_worker', once=True)
""".replace("MODE", repr(crash))
    result = installation.run("-c", script, check=False)
    assert result.returncode == 71, result.stdout + result.stderr
    installation.recover({"job": job})
    query(
        installation,
        "from apps.archive import models as m\nfrom apps.jobs.models import Job\n"
        "job=Job.objects.get(pk=data['job']); assert job.status=='SUCCEEDED',(job.status,job.error_code)\n"
        "assert job.attempt==2 and job.index_scan.completed\n"
        "assert m.ArchiveFile.objects.count()==1 and m.FileOperation.objects.count()==1\n"
        "assert m.SourceVersion.objects.count()==1 and not m.ArchiveFile.objects.usable().exists()\n",
        job,
    )
    assert len(list((installation.root / "clean").rglob("*.pdf"))) == 1
    assert not list((installation.root / "status" / ".staging").rglob("*.pdf"))


def test_failed_traversal_does_not_mark_known_sources_missing(indexed_installation):
    installation = indexed_installation
    enqueue(installation)
    installation.worker()
    job = enqueue(installation, "does-not-exist")
    installation.worker()
    query(
        installation,
        "from apps.archive import models as m\nfrom apps.jobs.models import Job\n"
        "job=Job.objects.get(pk=data['job']); assert job.status=='FAILED'\n"
        "assert job.index_scan.error_code=='INVENTORY_FAILED' and not job.index_scan.inventory_ready\n"
        "assert m.SourceFile.objects.get().presence=='PRESENT'\n",
        job,
    )


def test_changed_inventory_during_processing_never_claims_complete(indexed_installation):
    installation = indexed_installation
    job = enqueue(installation)
    script = """
import django
django.setup()
from django.core.management import call_command
from apps.archive import indexing
from django.conf import settings
from pathlib import Path
original = indexing._entry
def mutate(*args, **kwargs):
    original(*args, **kwargs)
    (Path(settings.SOURCE_DIR) / 'new.pdf').write_bytes(b'Synthetic owner addition')
indexing._entry = mutate
call_command('run_worker', once=True)
"""
    installation.run("-c", script)
    query(
        installation,
        "from apps.archive import models as m\nfrom apps.jobs.models import Job\n"
        "job=Job.objects.get(pk=data['job']); assert job.status=='FAILED'\n"
        "assert job.index_scan.error_code=='SOURCE_CHANGED' and not job.index_scan.completed\n"
        "assert m.SourceFolder.objects.get(relative_path='').index_state=='PARTIAL_FAILURE'\n",
        job,
    )
    assert not (installation.root / "status" / "INDEXSTATUS.json").exists()


def test_index_integrates_filename_and_actual_text_conflict_without_auto_approval(indexed_installation):
    installation = indexed_installation
    setup = """
from apps.catalog import models as c
from apps.catalog.services import save_record
from django.conf import settings
from pathlib import Path
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
import io
work=save_record(c.Work(title='Synthetic March'))
save_record(c.Arrangement(work=work, edition='Synthetic'))
variant=save_record(c.InstrumentVariant(name='Posaune', transposition='C', clef='BASS'))
for number in (1,2):
    save_record(c.Part(instrument=variant, code=str(number)))
writer=PdfWriter(); page=writer.add_blank_page(width=595.276,height=841.89)
font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
stream=DecodedStreamObject(); stream.set_data(b'BT /F1 12 Tf 50 800 Td (Synthetic March) Tj 0 -20 Td (Posaune 2) Tj ET')
page[NameObject('/Contents')]=writer._add_object(stream)
output=io.BytesIO(); writer.write(output)
(Path(settings.SOURCE_DIR)/'Synthetic March Posaune 1.pdf').write_bytes(output.getvalue())
"""
    installation.code(setup, {})
    before = raw_snapshot(installation.root / "raw")
    job = enqueue(installation)
    installation.worker()
    query(
        installation,
        "from apps.archive import models as m\nfrom apps.jobs.models import Job\n"
        "job=Job.objects.get(pk=data['job']); assert job.status=='SUCCEEDED',(job.status,job.error_code)\n"
        "file=m.ArchiveFile.objects.get(source_version__source_file__relative_path='Synthetic March Posaune 1.pdf')\n"
        "assert file.candidate_state=='CONFLICT' and file.review_state=='PENDING'\n"
        "assert file.candidates.get().method=='TEXT_LAYER'\n"
        "assert not file.assignments.exists() and not m.ArchiveFile.objects.usable().exists()\n",
        job,
    )
    assert raw_snapshot(installation.root / "raw") == before


def test_cancel_index_before_copy_does_not_make_files_available(indexed_installation):
    installation = indexed_installation
    job = enqueue(installation)
    script = """
import django
django.setup()
from django.core.management import call_command
from apps.archive import indexing
from apps.jobs.services.lifecycle import request_cancel
original = indexing._entry
def cancel(context, *args, **kwargs):
    request_cancel(context.job_id)
    return original(context, *args, **kwargs)
indexing._entry = cancel
call_command('run_worker', once=True)
"""
    before = raw_snapshot(installation.root / "raw")
    installation.run("-c", script)
    query(
        installation,
        "from apps.archive import models as m\nfrom apps.jobs.models import Job\n"
        "assert Job.objects.get(pk=data['job']).status=='CANCELLED'\n"
        "assert not m.ArchiveFile.objects.usable().exists()\n",
        job,
    )
    assert not list((installation.root / "clean").rglob("*.pdf"))
    assert raw_snapshot(installation.root / "raw") == before


def test_confirmed_copy_is_not_revoked_by_changed_or_missing_raw(indexed_installation):
    installation = indexed_installation
    identities = installation.action("setup")
    installation.worker()
    identities = installation.action("review", identities)
    installation.worker()
    approved = installation.action("check-approved", identities)
    raw = installation.root / "raw" / "correct.pdf"
    raw.write_bytes(raw.read_bytes() + b"\n% Changed synthetic source\n")
    job = enqueue(installation)
    installation.worker()
    query(
        installation,
        "from apps.archive import models as m\n"
        "assert m.ArchiveFile.objects.count()==2 and m.ArchiveFile.objects.usable().count()==1\n"
        "assert m.ArchiveFile.objects.filter(review_state='PENDING').count()==1\n",
        job,
    )
    raw.unlink()
    job = enqueue(installation)
    installation.worker()
    query(
        installation,
        "from apps.archive import models as m\n"
        "assert m.ArchiveFile.objects.usable().count()==1\n"
        "assert m.SourceFile.objects.get().presence=='MISSING'\n",
        job,
    )
    assert (installation.root / "clean" / approved["path"]).read_bytes() == synthetic_pdf()
