"""Participant-free contents artifact receipt and actual authenticated download bytes."""

import hashlib
from types import SimpleNamespace

from django.urls import reverse

from apps.exports import generation as g
from apps.exports.models import ExportCompletion, ExportPublication, ExportStage
from apps.exports.selection_services import authorize_selection, contents_report, selection_token
from apps.jobs.models import Job, OperationIntent
from apps.projects.preflight_services import fingerprint
from tests.pdf_fixtures import pdf
from tests.test_resolution import resolver_inputs as _resolution_fixture

resolver_inputs = _resolution_fixture


def test_contents_only_receipt_allows_exact_verified_download_without_participant(
    resolver_inputs, settings, tmp_path, client
):
    actor, project, *_ = resolver_inputs
    report = contents_report(project.pk)
    run = authorize_selection(report, selection_token(report, actor), [], actor)
    publication = ExportPublication.objects.create(run=run, relative_path=g.output_path(run.snapshot, {"id": None}))
    data = pdf()
    stage = ExportStage.objects.create(
        publication=publication,
        attempt=1,
        sha256=hashlib.sha256(data).hexdigest(),
        byte_size=len(data),
        manifest={
            "snapshot_id": str(run.snapshot_id),
            "snapshot_sha256": run.snapshot.sha256,
            "participant_id": None,
            "participant_name": "Inhaltsverzeichnis",
        },
    )
    intent = OperationIntent.objects.create(
        job=run.job,
        attempt=1,
        key=g.effect_key(publication),
        payload={"publication": str(publication.pk)},
        state="APPLIED",
        result=stage.receipt,
    )
    g.acknowledge(SimpleNamespace(job_id=run.job_id), intent)
    inventory = g.inventory(run)
    ExportCompletion.objects.create(run=run, inventory=inventory, sha256=fingerprint(inventory))
    settings.EXPORT_DIR = tmp_path / "export"
    path = settings.EXPORT_DIR / publication.relative_path
    path.parent.mkdir(parents=True)
    path.write_bytes(data)
    Job.objects.filter(pk=run.job_id).update(status="SUCCEEDED")
    artifact = run.artifacts.get()
    client.force_login(actor)
    response = client.get(reverse("generation_download", args=[artifact.pk]))
    assert response.status_code == 200 and b"".join(response.streaming_content) == data
    assert "Inhaltsverzeichnis.pdf" in response["Content-Disposition"] and artifact.participant_id is None
