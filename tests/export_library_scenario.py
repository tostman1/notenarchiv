"""Real Linux targeted regeneration and independent archive-reading publication."""

import json
import sys


def targeted(ids):
    from django.contrib.auth import get_user_model

    from apps.exports.models import GenerationRun
    from apps.exports.snapshot_services import authorize
    from apps.projects.models import ProjectParticipant
    from apps.projects.preflight_services import build_report, report_token

    old = GenerationRun.objects.get(pk=ids["run"])
    person = old.snapshot.participants.first()
    ProjectParticipant.objects.filter(pk=person.participant_id).update(display_name="Changed synthetic participant")
    actor = get_user_model().objects.get(pk=ids["actor"])
    report = build_report(old.snapshot.project_id, participant_ids=[person.participant_id])
    run = authorize(
        old.snapshot.project_id,
        participant_ids=[person.participant_id],
        position_ids=list(report.session.positions),
        token=report_token(report, actor),
        acknowledgements=sorted(report.missing_keys),
        actor=actor,
    )
    return {**ids, "run": str(run.pk), "job": str(run.job_id), "old": str(old.pk)}


def archive(ids):
    from django.contrib.auth import get_user_model

    from apps.exports import archive_services

    actor = get_user_model().objects.get(pk=ids["actor"])
    import hashlib

    from apps.archive import models as m
    from apps.archive import publication as p
    from apps.archive import services as s
    from apps.jobs.services.worker import run_worker
    from config.env import env

    original = m.ArchiveFile.objects.get(pk=ids["file"])
    # The test owner prepares a second deliberate source identity; real app copy/
    # inspection/approval services are used, never a forged available archive file.
    data = (env.source_dir / "correct.pdf").read_bytes()
    second_source = env.source_dir / "correct-second.pdf"
    if not second_source.exists():
        second_source.write_bytes(data)
    version, _ = s.observe_version(
        original.source_version.source_file.folder_id,
        "correct-second.pdf",
        sha256=hashlib.sha256(data).hexdigest(),
        byte_size=len(data),
        pdf_state="VALID",
        page_info=original.source_version.page_info,
    )
    second, job = p.queue_copy(version.pk)
    run_worker(env.database_path.parent / "worker.lock", once=True)
    second.refresh_from_db()
    proposal = s.create_proposal(
        second.pk,
        actor=actor,
        arrangement_id=original.arrangement_id,
        part_ids=[original.assignments.usable().first().part_id],
        expected_revision=second.revision,
    )
    second.refresh_from_db()
    s.record_inspection(
        proposal.pk, actor=actor, inspected_sha256=second.sha256, explicit=True, expected_revision=second.revision
    )
    second.refresh_from_db()
    p.queue_canonical(proposal.pk, actor=actor, expected_revision=second.revision)
    run_worker(env.database_path.parent / "worker.lock", once=True)
    selected = archive_services.report([ids["file"], second.pk])
    token = archive_services.token(selected, actor, "READING")
    identifiers = [f.pk for f in selected]
    run = archive_services.authorize(identifiers, token, actor, variant="READING")
    assert archive_services.authorize(identifiers, token, actor, variant="READING").pk == run.pk
    return {**ids, "run": str(run.pk), "job": str(run.job_id)}


def check(ids):
    from apps.exports.generation import verified_complete
    from apps.exports.library_services import classify
    from apps.exports.models import GenerationRun

    run = GenerationRun.objects.get(pk=ids["run"])
    assert verified_complete(run), (run.job.status, run.job.error_code)
    assert all(classify(a).output == "VERIFIED" for a in run.artifacts.all())
    if "old" in ids:
        old = GenerationRun.objects.get(pk=ids["old"])
        assert old.artifacts.count() == 2 and run.artifacts.count() == 1
        changed = [classify(a) for a in old.artifacts.all()]
        assert sum(s.stale for s in changed) == 1 and all(s.reproducible for s in changed)
    else:
        assert run.snapshot.project_id is None and run.snapshot.kind == "ARCHIVE_NOTES"
        assert run.snapshot.payload["output_variant"] == "READING"
        assert run.snapshot.inputs.count() == 2 and run.artifacts.get().manifest["page_count"] == 2
    return {"ok": True}


if __name__ == "__main__":
    import django

    django.setup()
    action, ids = sys.argv[1], json.loads(sys.argv[2])
    result = targeted(ids) if action == "targeted" else archive(ids) if action == "archive" else check(ids)
    sys.stdout.write("SCENARIO_RESULT=" + json.dumps(result) + "\n")
