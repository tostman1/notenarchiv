"""Actual PDF review browser; Linux performs real canonical worker publication."""

import hashlib
import os
import subprocess
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import connections

from apps.archive import models as m
from apps.archive.recognition import build_rule_set, record_candidate
from apps.archive.services import observe_version, record_validation, register_base
from apps.catalog import models as c
from apps.jobs.models import Job, WorkerLease
from apps.jobs.services.worker import run_worker
from tests.archive_fixtures import PAGE
from tests.pdf_fixtures import A4, pdf
from tests.test_archive_workflow import receipt


@pytest.mark.django_db(transaction=True)
def test_explicit_review_and_canonical_publication_in_browser(settings, tmp_path, request, monkeypatch):
    settings.STATIC_ROOT = tmp_path / "static"
    settings.DEBUG_MODE = False
    for setting, name in (
        ("SOURCE_DIR", "raw"),
        ("CURATED_DIR", "clean"),
        ("PROCESSED_DIR", "processed"),
        ("STATUS_DIR", "status"),
    ):
        path = tmp_path / name
        path.mkdir()
        setattr(settings, setting, path)
    WorkerLease.objects.get_or_create(pk=1)
    call_command("collectstatic", interactive=False, verbosity=0)
    actor = get_user_model().objects.create_user("review-browser", password="Synthetic-review-135")
    work = c.Work.objects.create(title="Synthetic review")
    arrangement = c.Arrangement.objects.create(work=work, edition="Synthetic edition")
    variant = c.InstrumentVariant.objects.create(name="Posaune", transposition="C", clef="BASS")
    parts = [c.Part.objects.create(instrument=variant, code=str(n)) for n in (2, 3)]
    folder = m.SourceFolder.objects.create(relative_path="Synthetic")
    data = pdf(sizes=(A4, A4))
    version, _ = observe_version(
        folder.pk,
        "Synthetic/Synthetic review Posaune 1.pdf",
        sha256=hashlib.sha256(data).hexdigest(),
        byte_size=len(data),
        pdf_state="UNCHECKED",
    )
    version = record_validation(
        version.pk,
        expected_revision=version.revision,
        pdf_state="VALID",
        page_info=[PAGE, PAGE],
        original_crop_boxes=[PAGE["crop_box"], PAGE["crop_box"]],
    )
    file, _ = receipt(register_base(version.pk, "_Ungeprueft/review.pdf"))
    record_candidate(
        version.pk, filename="Synthetic review Posaune 1.pdf", text_lines=["Synthetic review", "Posaune 2"]
    )
    evidence = m.OcrPageEvidence.objects.create(
        source_version=version,
        cache_key="6" * 64,
        page=1,
        evidence={
            "sha256": version.sha256,
            "cache_key": "6" * 64,
            "page": 1,
            "bounds": [0, 0, 200, 300],
            "orientation": 0,
            "rules": build_rule_set().version,
            "text_layer": "",
            "words": [],
        },
    )
    record_candidate(version.pk, filename="Synthetic review Posaune 1.pdf", ocr_evidence=evidence)
    path = settings.CURATED_DIR / file.relative_path
    path.parent.mkdir()
    path.write_bytes(data)
    (settings.SOURCE_DIR / "synthetic.pdf").write_bytes(data)
    before = (settings.SOURCE_DIR / "synthetic.pdf").read_bytes()
    server = request.getfixturevalue("live_server")
    arguments = [server.url, str(file.pk), str(arrangement.pk), str(variant.pk), *[str(p.pk) for p in parts]]
    script = str(Path(__file__).with_name("review.cjs"))
    subprocess.run(["node", script, "selection", *arguments], check=True, timeout=90)
    job = Job.objects.get(kind="OCR")
    assert job.payload["selection"] == {"page": 1, "box": [0.1, 0.2, 0.8, 0.9]}
    assert not m.ReviewInspection.objects.exists() and not m.ArchiveProposal.objects.exists()
    # This browser case verifies enqueue, not native OCR execution (container smoke).
    Job.objects.filter(pk=job.pk).delete()
    subprocess.run(["node", script, "region", *arguments], check=True, timeout=90)
    revisions = list(m.PageRegionRevision.objects.order_by("number"))
    assert [revision.number for revision in revisions] == [1, 2]
    assert revisions[0].region_id == revisions[1].region_id
    assert revisions[0].bounds_points != revisions[1].bounds_points
    assert not m.ContentInspection.objects.exists() and not m.ContentConfirmation.objects.exists()
    assert not m.ReviewInspection.objects.exists() and not m.ArchiveProposal.objects.exists()
    subprocess.run(["node", script, "content", *arguments], check=True, timeout=90)
    content = m.ContentEditionRevision.objects.get()
    references = list(content.references.order_by("sequence"))
    assert len(references) == 2 and references[0].pk != references[1].pk
    assert references[0].logical_page_revision_id == references[1].logical_page_revision_id
    assert references[0].logical_page_revision.region_revision_id == revisions[1].pk
    assert not m.ContentInspection.objects.exists() and not m.ContentConfirmation.objects.exists()
    assert not m.ReviewInspection.objects.exists() and not m.ArchiveProposal.objects.exists()
    subprocess.run(["node", script, "content-review", *arguments], check=True, timeout=90)
    inspection = m.ContentInspection.objects.get()
    confirmation = m.ContentConfirmation.objects.get()
    assert inspection.revision_id == content.pk and inspection.visually_reviewed
    assert confirmation.inspection_id == inspection.pk and confirmation.actor_id == inspection.reviewer_id
    assert not m.ReviewInspection.objects.exists() and not m.ArchiveProposal.objects.exists()
    subprocess.run(["node", script, "split", *arguments], check=True, timeout=90)
    children = list(m.PageRegionRevision.objects.exclude(pk__in=[revision.pk for revision in revisions]))
    assert len(children) == 2 and children[0].region_id != children[1].region_id
    assert all(child.number == 1 and child.region.source_page.page_index == 1 for child in children)
    assert m.PageRegionRevision.objects.filter(pk=revisions[1].pk).exists()
    assert references[0].logical_page_revision.region_revision_id == revisions[1].pk
    assert m.ContentInspection.objects.count() == m.ContentConfirmation.objects.count() == 1
    assert m.ContentEditionRevision.objects.count() == 1
    assert not m.ReviewInspection.objects.exists() and not m.ArchiveProposal.objects.exists()
    subprocess.run(["node", script, "merge", *arguments], check=True, timeout=90)
    merged = m.PageRegionRevision.objects.exclude(pk__in=[revision.pk for revision in [*revisions, *children]]).get()
    assert merged.region_id not in {child.region_id for child in children}
    assert merged.bounds_points == [
        min(child.bounds_points[0] for child in children),
        min(child.bounds_points[1] for child in children),
        max(child.bounds_points[2] for child in children),
        max(child.bounds_points[3] for child in children),
    ]
    assert m.ContentInspection.objects.count() == m.ContentConfirmation.objects.count() == 1
    persisted_references = list(content.references.select_related("logical_page_revision").order_by("sequence"))
    assert [reference.pk for reference in persisted_references] == [reference.pk for reference in references]
    assert [reference.logical_page_revision_id for reference in persisted_references] == [
        reference.logical_page_revision_id for reference in references
    ]
    assert all(
        reference.logical_page_revision.region_revision_id == revisions[1].pk for reference in persisted_references
    )
    persisted_inspection = m.ContentInspection.objects.get(pk=inspection.pk)
    persisted_confirmation = m.ContentConfirmation.objects.get(pk=confirmation.pk)
    assert persisted_inspection.revision_id == content.pk and persisted_inspection.reviewer_id == inspection.reviewer_id
    assert (
        persisted_confirmation.inspection_id == inspection.pk
        and persisted_confirmation.actor_id == confirmation.actor_id
    )
    for original in [*revisions, *children]:
        persisted = m.PageRegionRevision.objects.get(pk=original.pk)
        assert persisted.region_id == original.region_id and persisted.number == original.number
        assert (
            persisted.bounds_points == original.bounds_points
            and persisted.page_fingerprint == original.page_fingerprint
        )
    subprocess.run(["node", script, "inspect", *arguments], check=True, timeout=90)
    file.refresh_from_db()
    assert file.current_proposal.parts.count() == 2 and file.current_proposal.inspections.get().reviewer_id == actor.pk
    assert not m.ArchiveFile.objects.usable().exists()
    if os.name == "posix":
        from apps.archive import review_services

        original, failures = review_services.act, []

        def diagnostic(*args, **kwargs):
            try:
                return original(*args, **kwargs)
            except Exception as error:
                # Synthetic fixtures only; never enable exception output in the app.
                failures.append((type(error).__name__, str(error)))
                raise

        monkeypatch.setattr(review_services, "act", diagnostic)
        result = subprocess.run(["node", script, "approve", *arguments], check=False, timeout=90)
        assert result.returncode == 0, failures
        assert Job.objects.filter(kind="ARCHIVE_PUBLISH", status="QUEUED").count() == 1
        run_worker(Path(connections["default"].settings_dict["NAME"]).parent / "worker.lock", once=True)
        file.refresh_from_db()
        assert file.review_state == "CONFIRMED" and file.assignments.usable().count() == 2
        assert (settings.CURATED_DIR / file.relative_path).read_bytes() == data
        subprocess.run(["node", script, "confirmed", *arguments], check=True, timeout=60)
    assert (settings.SOURCE_DIR / "synthetic.pdf").read_bytes() == before
