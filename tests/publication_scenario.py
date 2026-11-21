"""Synthetic subprocess/container acceptance driver; never installed in the image."""

import base64
import hashlib
import io
import json
import os
import sys
from dataclasses import asdict, replace


def synthetic_pdf():
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=595.276, height=841.89)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def setup(collision=None):
    from django.contrib.auth import get_user_model

    from apps.archive import models as m
    from apps.archive import publication as p
    from apps.archive import services as s
    from apps.catalog import models as catalog
    from apps.catalog.services import save_record
    from config.env import env
    from core.pdf import Processor

    data = synthetic_pdf()
    assert (env.source_dir / "correct.pdf").read_bytes() == data
    scratch = env.database_path.parent / "scenario-scratch"
    scratch.mkdir(mode=0o700, exist_ok=True)
    info = Processor(scratch).inspect(data)
    folder = m.SourceFolder.objects.create(relative_path="")
    version, _ = s.observe_version(
        folder.pk,
        "correct.pdf",
        sha256=hashlib.sha256(data).hexdigest(),
        byte_size=len(data),
        pdf_state="VALID",
        page_info=[asdict(page) for page in info.pages],
    )
    if collision:
        existing = (
            env.curated_dir
            / "_Ungeprueft"
            / version.source_file_id.hex
            / ("CORRECT.PDF" if collision == "case" else "correct.pdf")
        )
        existing.parent.mkdir(mode=0o750, parents=True)
        existing.write_bytes(data if collision == "same" else b"Synthetic existing history")
    file, job = p.queue_copy(version.pk)
    actor = get_user_model().objects.create_user("synthetic-publication-reviewer")
    work = save_record(catalog.Work(title="Bereits korrekt"))
    arrangement = save_record(catalog.Arrangement(work=work, edition="Testfassung"))
    variant = save_record(catalog.InstrumentVariant(name="Posaune", transposition="B", clef="BASS"))
    parts = [save_record(catalog.Part(instrument=variant, code=str(n))) for n in (2, 3)]
    return {
        "file": str(file.pk),
        "version": str(version.pk),
        "job": str(job.pk),
        "actor": actor.pk,
        "arrangement": str(arrangement.pk),
        "parts": [str(part.pk) for part in parts],
    }


def review(identities, *, corrected=False):
    from apps.archive import models as m
    from apps.archive import publication as p
    from apps.archive import services as s

    file = m.ArchiveFile.objects.get(pk=identities["file"])
    parts = identities["parts"][:1] if corrected else identities["parts"]
    proposal = s.create_proposal(
        file.pk,
        actor=identities["actor"],
        arrangement_id=identities["arrangement"],
        part_ids=parts,
        expected_revision=file.revision,
    )
    file.refresh_from_db()
    s.record_inspection(
        proposal.pk,
        actor=identities["actor"],
        inspected_sha256=file.sha256,
        explicit=True,
        expected_revision=file.revision,
    )
    file.refresh_from_db()
    job = p.queue_canonical(proposal.pk, actor=identities["actor"], expected_revision=file.revision)
    return {**identities, "job": str(job.pk), "proposal": str(proposal.pk)}


def check(identities, *, approved=False):
    from apps.archive import models as m
    from apps.archive import publication as p
    from apps.jobs.models import Job
    from config.env import env

    file = m.ArchiveFile.objects.get(pk=identities["file"])
    job = Job.objects.get(pk=identities["job"])
    assert job.status == "SUCCEEDED", (job.status, job.error_code)
    assert file.publication_state == "AVAILABLE"
    assert p.verified_bytes(file.pk) == synthetic_pdf()
    target = env.curated_dir / file.relative_path
    assert target.stat().st_nlink == 1
    if (env.source_dir / "correct.pdf").exists():
        assert target.stat().st_ino != (env.source_dir / "correct.pdf").stat().st_ino
    if approved:
        assert file.review_state == "CONFIRMED" and file.arrangement_id is not None
        assert file.assignments.usable().count() == len(identities["parts"])
        assert m.ArchiveFile.objects.usable().filter(pk=file.pk).exists()
        for operation in file.operations.filter(state="APPLIED"):
            assert (env.curated_dir / operation.target_path).read_bytes() == synthetic_pdf()
    else:
        assert file.arrangement_id is None and file.review_state == "PENDING" and not file.assignments.exists()
        assert not m.ArchiveFile.objects.usable().exists()
    return {"path": file.relative_path, "sha256": file.sha256, "operations": file.operations.count()}


def interrupted(mode):
    from django.db.models import F

    from apps.archive import publication as p
    from apps.jobs.models import WorkerLease
    from apps.jobs.services import lifecycle, queue, worker
    from config.env import env

    if mode == "crash-during-copy":
        original = p.files.os.write

        def partial(descriptor, data):
            original(descriptor, data[:37])
            os._exit(24)

        p.files.os.write = partial
    elif mode == "crash-after-link":
        original = p.files.publish

        def link(*args):
            original(*args)
            os._exit(23)

        p.files.publish = link
    elif mode == "crash-inside-ack":
        original = p.acknowledge

        def acknowledgement(*args):
            original(*args)
            os._exit(25)

        queue.HANDLERS["ARCHIVE_PUBLISH"] = replace(queue.HANDLERS["ARCHIVE_PUBLISH"], acknowledge=acknowledgement)
    elif mode == "crash-after-commit":
        original = worker.JobContext.publish

        def committed(*args):
            original(*args)
            os._exit(26)

        worker.JobContext.publish = committed
    elif mode in {"cancel-before-publish", "fence-before-publish"}:
        original = p.files.stage_copy

        def staged(*args, **kwargs):
            result = original(*args, **kwargs)
            context = kwargs["checkpoint"].__self__
            if mode == "cancel-before-publish":
                lifecycle.request_cancel(context.job_id)
            else:
                WorkerLease.objects.filter(pk=1).update(generation=F("generation") + 1)
            return result

        p.files.stage_copy = staged
    worker.run_worker(env.database_path.parent / "worker.lock", once=True)


def main():
    action = sys.argv[1]
    if action == "pdf":
        sys.stdout.write(base64.b64encode(synthetic_pdf()).decode())
        return
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django

    django.setup()
    if action == "setup":
        result = setup(sys.argv[2] if len(sys.argv) > 2 else None)
    elif action in {"review", "correct"}:
        result = review(json.loads(sys.argv[2]), corrected=action == "correct")
    elif action in {"check-copy", "check-approved"}:
        result = check(json.loads(sys.argv[2]), approved=action == "check-approved")
    else:
        interrupted(action)
        result = {"finished": True}
    sys.stdout.write("SCENARIO_RESULT=" + json.dumps(result) + "\n")


if __name__ == "__main__":
    main()
