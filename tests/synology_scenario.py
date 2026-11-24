"""Synthetic stack control/inspection; not shipped in the application image."""

import json
import sys

import django

django.setup()

from django.contrib.auth import get_user_model  # noqa: E402

from apps.archive import models as archive  # noqa: E402
from apps.catalog import models as catalog  # noqa: E402
from apps.exports.models import GenerationRun  # noqa: E402
from apps.jobs.models import Job  # noqa: E402
from apps.members.models import Member  # noqa: E402
from apps.projects import models as projects  # noqa: E402


def setup():
    instrument = catalog.InstrumentVariant.objects.create(name="Posaune", clef="BASS", transposition="C")
    parts = [catalog.Part.objects.create(instrument=instrument, code=str(n)) for n in (1, 2, 3)]
    members = [Member.objects.create(name=f"Testperson {n}", regular_part=part) for n, part in enumerate(parts, 1)]
    arrangements = []
    for title in ("Testmarsch Alpha", "Testpolka Beta", "Testwalzer Gamma"):
        work = catalog.Work.objects.create(title=title)
        arrangements.append(catalog.Arrangement.objects.create(work=work, edition="Synthetisch"))
    actor = get_user_model().objects.get(username="synthetic-archivist")
    project = projects.Project.objects.create(name="Synthetische Testmappe", cover_enabled=True)
    people = [
        projects.ProjectParticipant.objects.create(
            project=project, member=member, display_name=member.name, default_part=member.regular_part
        )
        for member in members
    ]
    positions = []
    for n, arrangement in enumerate([arrangements[0], None, *arrangements[1:]], 1):
        positions.append(projects.ProjectPosition.objects.create(project=project, order=n, arrangement=arrangement))
    projects.GlobalRuleState.objects.get_or_create(pk=1)
    return {
        "actor": actor.pk,
        "instrument": str(instrument.pk),
        "parts": [str(p.pk) for p in parts],
        "arrangements": {a.work.title: str(a.pk) for a in arrangements},
        "project": str(project.pk),
        "people": [str(p.pk) for p in people],
        "positions": [str(p.pk) for p in positions],
    }


def files():
    return [
        {
            "id": str(file.pk),
            "path": file.source_version.source_file.relative_path,
            "review": file.review_state,
            "publication": file.publication_state,
        }
        for file in archive.ArchiveFile.objects.select_related("source_version__source_file")
    ]


def run_state(ids):
    run = GenerationRun.objects.select_related("job").get(pk=ids["run"])
    return {
        "status": run.job.status,
        "attempt": run.job.attempt,
        "error": run.job.error_code,
        "artifacts": [str(a.pk) for a in run.artifacts.all()],
    }


def authorize(ids):
    from apps.exports.snapshot_services import authorize
    from apps.projects.preflight_services import build_report, report_token

    actor = get_user_model().objects.get(pk=ids["actor"])
    report = build_report(ids["project"])
    run = authorize(
        ids["project"],
        participant_ids=list(report.session.participants),
        position_ids=list(report.session.positions),
        token=report_token(report, actor),
        acknowledgements=sorted(report.missing_keys),
        actor=actor,
    )
    return {**ids, "run": str(run.pk), "job": str(run.job_id)}


def check_pins(ids):
    from django.db.models.deletion import ProtectedError

    run = GenerationRun.objects.get(pk=ids["run"])
    pinned = run.snapshot.inputs.first()
    assert pinned is not None
    try:
        archive.SourceVersion.objects.filter(pk=pinned.source_version_id).delete()
    except ProtectedError:
        pass
    else:
        raise AssertionError("Exact version protection failed")
    return {"protected": True}


def outputs():
    from io import BytesIO

    from pypdf import PdfReader

    from apps.exports.generation import verified_complete
    from apps.exports.models import ExportArtifact
    from config.env import env

    variants, sizes = set(), set()
    for artifact in ExportArtifact.objects.select_related("run__snapshot", "run__job"):
        if artifact.run.job.status != "SUCCEEDED":
            continue
        assert verified_complete(artifact.run)
        data = (env.export_dir / artifact.relative_path).read_bytes()
        import hashlib

        assert hashlib.sha256(data).hexdigest() == artifact.sha256
        reader = PdfReader(BytesIO(data))
        variants.add((artifact.run.snapshot.kind, artifact.variant))
        if artifact.variant == "PRINT":
            for page in reader.pages:
                sizes.add((round(float(page.mediabox.width)), round(float(page.mediabox.height))))
    assert {("FULL", "READING"), ("FULL", "PRINT"), ("EXCERPT", "READING"), ("CONTENTS", "READING")} <= variants
    assert (1191, 842) in sizes and (595, 842) in sizes
    return {"verified": True}


action = sys.argv[1]
ids = json.loads(sys.argv[2]) if len(sys.argv) > 2 else None
if action == "setup":
    result = setup()
elif action == "files":
    result = files()
elif action == "authorize":
    result = authorize(ids)
elif action == "state":
    result = run_state(ids)
elif action == "pins":
    result = check_pins(ids)
elif action == "outputs":
    result = outputs()
elif action == "jobs":
    result = list(Job.objects.values("id", "status", "error_code", "attempt"))
else:
    raise ValueError(action)
sys.stdout.write("SCENARIO_RESULT=" + json.dumps(result, default=str) + "\n")
