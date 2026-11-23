"""Synthetic excerpt/contents/historical independent process and container driver."""

import json
import sys


def authorize(ids, kind):
    from django.contrib.auth import get_user_model

    from apps.exports.models import GenerationRun
    from apps.exports.selection_services import authorize_selection, contents_report, historical_report, selection_token
    from apps.exports.snapshot_services import authorize as current
    from apps.projects.preflight_services import build_report, report_token

    old = GenerationRun.objects.get(pk=ids["run"])
    actor = get_user_model().objects.get(pk=ids["actor"])
    people = [p["id"] for p in old.snapshot.payload["participants"]]
    positions = [old.snapshot.payload["positions"][0]["id"]]
    if kind == "EXCERPT":
        report = build_report(old.snapshot.project_id, participant_ids=people, position_ids=positions)
        run = current(
            old.snapshot.project_id,
            participant_ids=people,
            position_ids=positions,
            token=report_token(report, actor),
            acknowledgements=sorted(report.missing_keys),
            actor=actor,
            kind=kind,
        )
    else:
        report = (
            contents_report(old.snapshot.project_id)
            if kind == "CONTENTS"
            else historical_report(old.snapshot_id, people[:1], positions)
        )
        run = authorize_selection(report, selection_token(report, actor), report.missing, actor)
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
        data = preview.snapshot(
            env.export_dir,
            artifact.relative_path,
            maximum=artifact.byte_size,
            sha256=artifact.sha256,
            size=artifact.byte_size,
        )
        reader = PdfReader(BytesIO(data))
        assert len(reader.pages) == 1
        if run.snapshot.kind == "CONTENTS":
            assert artifact.participant_id is None and "Inhaltsverzeichnis" in reader.pages[0].extract_text()
            assert "2. Reserve" in reader.pages[0].extract_text()
            assert "Noten fehlen" not in reader.pages[0].extract_text()
        else:
            assert artifact.participant_id and not reader.pages[0].extract_text()
    return {"kind": run.snapshot.kind, "artifacts": run.artifacts.count()}


if __name__ == "__main__":
    import django

    django.setup()
    action, ids = sys.argv[1], json.loads(sys.argv[2])
    result = check(ids) if action == "check" else authorize(ids, action)
    sys.stdout.write("SCENARIO_RESULT=" + json.dumps(result) + "\n")
