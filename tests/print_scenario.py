"""Synthetic print publication acceptance for independent processes and containers."""

import json
import sys


def authorize(ids, kind):
    from django.contrib.auth import get_user_model

    from apps.exports import archive_services, print_services
    from apps.exports.models import GenerationRun

    old = GenerationRun.objects.get(pk=ids["run"])
    actor = get_user_model().objects.get(pk=ids["actor"])
    if kind == "ARCHIVE":
        selected = archive_services.report([ids["file"]])
        run = archive_services.authorize([ids["file"]], archive_services.token(selected, actor), actor)
    else:
        run = print_services.authorize_print(old.snapshot_id, print_services.token(old.snapshot, actor), actor)
    return {**ids, "run": str(run.pk), "job": str(run.job_id)}


def check(ids):
    from io import BytesIO

    from pypdf import PdfReader

    from apps.exports.generation import verified_complete
    from apps.exports.models import GenerationRun
    from config.env import env
    from core import preview

    run = GenerationRun.objects.get(pk=ids["run"])
    assert verified_complete(run), (run.job.status, run.job.error_code)
    for artifact in run.artifacts.all():
        assert artifact.variant == "PRINT" and artifact.manifest["print_plan"]
        data = preview.snapshot(
            env.export_dir,
            artifact.relative_path,
            maximum=artifact.byte_size,
            sha256=artifact.sha256,
            size=artifact.byte_size,
        )
        reader = PdfReader(BytesIO(data))
        assert len(reader.pages) == len(artifact.manifest["print_plan"]["sheets"])
    return {"artifacts": run.artifacts.count()}


if __name__ == "__main__":
    import django

    django.setup()
    action, ids = sys.argv[1], json.loads(sys.argv[2])
    result = check(ids) if action == "check" else authorize(ids, action)
    sys.stdout.write("SCENARIO_RESULT=" + json.dumps(result) + "\n")
