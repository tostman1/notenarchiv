"""Synthetic independent-process export acceptance; never installed in the image."""

import json
import os
import sys
import uuid
from dataclasses import replace


def setup(ids):
    from django.contrib.auth import get_user_model

    from apps.archive.models import ArchiveFile
    from apps.exports.snapshot_services import authorize
    from apps.projects.models import GlobalRuleState, Project, ProjectParticipant, ProjectPosition
    from apps.projects.preflight_services import build_report, report_token

    GlobalRuleState.objects.get_or_create(pk=1)
    project = Project.objects.create(name="Synthetische Mappen", cover_enabled=True)
    file = ArchiveFile.objects.get(pk=ids["file"])
    for n, part in enumerate(ids["parts"]):
        ProjectParticipant.objects.create(
            project=project, guest_id=uuid.uuid4(), display_name=f"Synthetische Person {n}", default_part_id=part
        )
    for number in (1, 2, 3):
        ProjectPosition.objects.create(
            project=project, order=number, arrangement_id=file.arrangement_id if number != 2 else None
        )
    actor = get_user_model().objects.get(pk=ids["actor"])
    report = build_report(project.pk)
    run = authorize(
        project.pk,
        participant_ids=list(report.session.participants),
        position_ids=list(report.session.positions),
        token=report_token(report, actor),
        acknowledgements=sorted(report.missing_keys),
        actor=actor,
    )
    return {**ids, "run": str(run.pk), "job": str(run.job_id)}


def interrupt(mode):
    from apps.exports import generation as g
    from apps.jobs.services import lifecycle, queue, worker
    from config.env import env

    original_checkpoint = worker.JobContext.checkpoint
    if mode == "crash-before-composition":

        def compose(*args, **kwargs):
            os._exit(30)

        g._compose = compose
    elif mode in {"crash-during-stage", "cancel-during-stage"}:
        original = g.files.os.write

        def write(fd, data):
            result = original(fd, data[:37])
            if mode.startswith("crash"):
                os._exit(31)
            from apps.jobs.models import Job

            lifecycle.request_cancel(Job.objects.get(status="RUNNING").pk)
            return result

        g.files.os.write = write
    elif mode in {"crash-after-link", "crash-after-first-participant"}:
        original = g.files.publish
        count = 0

        def publish(*args):
            nonlocal count
            count += 1
            original(*args)
            if mode == "crash-after-link" or count == 2:
                os._exit(32)

        g.files.publish = publish
    elif mode == "crash-inside-ack":
        original = g.acknowledge

        def acknowledge(*args):
            original(*args)
            os._exit(33)

        queue.HANDLERS["GENERATE"] = replace(queue.HANDLERS["GENERATE"], acknowledge=acknowledge)
    elif mode == "crash-after-commit":
        original = worker.JobContext.publish

        def committed(*args):
            original(*args)
            os._exit(34)

        worker.JobContext.publish = committed
    elif mode == "crash-during-composition":
        original = g.Processor.compose

        def compose(processor, *args, **kwargs):
            count = 0

            def crash():
                nonlocal count
                count += 1
                if count == 5:
                    os._exit(37)
                processor.checkpoint()

            return original(g.Processor(processor.root, checkpoint=crash), *args, **kwargs)

        g.Processor.compose = compose
    elif mode == "cancel-during-composition":
        original = g.Processor.compose

        def compose(processor, *args, **kwargs):
            from apps.jobs.models import Job

            count = 0

            def cancel():
                nonlocal count
                count += 1
                # _invoke stages both inputs, run_process checks once before
                # launch, then checks again while the actual child is running.
                if count == 5:
                    lifecycle.request_cancel(Job.objects.get(status="RUNNING").pk)
                processor.checkpoint()

            child = g.Processor(processor.root, checkpoint=cancel)
            return original(child, *args, **kwargs)

        g.Processor.compose = compose
    elif mode == "cancel-after-stage":
        original = g.stage_bytes

        def staged(*args, **kwargs):
            from apps.jobs.models import Job

            result = original(*args, **kwargs)
            lifecycle.request_cancel(Job.objects.get(status="RUNNING").pk)
            return result

        g.stage_bytes = staged
    elif mode == "fail-second-participant":
        original = g._compose
        count = 0

        def compose(*args, **kwargs):
            nonlocal count
            count += 1
            if count == 2:
                raise ValueError("Synthetic second participant failure")
            return original(*args, **kwargs)

        g._compose = compose
    elif mode in {"crash-after-completion", "crash-after-stage-record"}:
        original = worker.JobContext.commit_metadata

        def metadata(*args):
            from apps.exports.models import ExportCompletion, ExportStage

            result = original(*args)
            if mode == "crash-after-stage-record" and ExportStage.objects.exists():
                os._exit(36)
            if mode == "crash-after-completion" and ExportCompletion.objects.exists():
                os._exit(35)
            return result

        worker.JobContext.commit_metadata = metadata
    else:
        raise ValueError(mode)
    worker.run_worker(env.database_path.parent / "worker.lock", once=True)
    worker.JobContext.checkpoint = original_checkpoint
    return {"finished": True}


def check(ids):
    from apps.exports.generation import inventory, is_complete
    from apps.exports.models import GenerationRun
    from config.env import env
    from core import preview

    run = GenerationRun.objects.get(pk=ids["run"])
    assert is_complete(run), (run.job.status, run.job.error_code)
    for artifact in run.artifacts.all():
        assert preview.snapshot(
            env.export_dir,
            artifact.relative_path,
            maximum=artifact.byte_size,
            sha256=artifact.sha256,
            size=artifact.byte_size,
        )
        assert artifact.manifest["page_count"] == 4
        assert [p["number"] for p in artifact.manifest["positions"]] == [1, 2, 3]
    return {"inventory": inventory(run), "attempt": run.job.attempt}


if __name__ == "__main__":
    import django

    django.setup()
    action = sys.argv[1]
    ids = json.loads(sys.argv[2]) if len(sys.argv) > 2 else None
    result = setup(ids) if action == "setup" else check(ids) if action == "check" else interrupt(action)
    sys.stdout.write("SCENARIO_RESULT=" + json.dumps(result) + "\n")
