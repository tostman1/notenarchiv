"""Synthetic artifact receipts, immutable history and authenticated negative downloads."""

import hashlib

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.urls import reverse

from apps.exports import generation as g
from apps.exports.models import ExportCompletion, ExportPublication, ExportStage
from apps.exports.snapshot_services import authorize
from apps.jobs.models import OperationIntent
from apps.projects.preflight_services import fingerprint
from tests.pdf_fixtures import pdf
from tests.test_generation_snapshots import permission
from tests.test_resolution import resolver_inputs as _resolution_fixture

resolver_inputs = _resolution_fixture


def completed(inputs, settings, tmp_path):
    run = authorize(**permission(inputs))
    person = run.snapshot.payload["participants"][0]
    path = g.output_path(run.snapshot, person)
    publication = ExportPublication.objects.create(run=run, participant_id=person["id"], relative_path=path)
    data = pdf()
    stage = ExportStage.objects.create(
        publication=publication,
        attempt=1,
        sha256=hashlib.sha256(data).hexdigest(),
        byte_size=len(data),
        manifest={
            "participant_name": person["name"],
            "participant_id": person["id"],
            "snapshot_id": str(run.snapshot_id),
            "snapshot_sha256": run.snapshot.sha256,
        },
    )
    intent = OperationIntent.objects.create(
        job=run.job,
        attempt=1,
        key="artifact:" + publication.participant_id.hex,
        payload={"publication": str(publication.pk)},
        state="APPLIED",
        result=stage.receipt,
    )
    from types import SimpleNamespace

    g.acknowledge(SimpleNamespace(job_id=run.job_id), intent)
    settings.EXPORT_DIR = tmp_path / "export"
    file = settings.EXPORT_DIR / path
    file.parent.mkdir(parents=True)
    file.write_bytes(data)
    inventory = g.inventory(run)
    ExportCompletion.objects.create(run=run, inventory=inventory, sha256=fingerprint(inventory))
    from apps.jobs.models import Job

    Job.objects.filter(pk=run.job_id).update(status="SUCCEEDED")
    run.job.refresh_from_db()
    return run, run.artifacts.get(), file, data


def test_download_requires_login_complete_run_and_exact_hash(resolver_inputs, settings, tmp_path, client):
    run, artifact, path, data = completed(resolver_inputs, settings, tmp_path)
    url = reverse("generation_download", args=[artifact.pk])
    assert client.get(url).status_code == 302
    client.force_login(resolver_inputs[0])
    response = client.get(url)
    assert response.status_code == 200 and b"".join(response.streaming_content) == data
    assert response["X-Content-Type-Options"] == "nosniff"
    assert "attachment" in response["Content-Disposition"] and "no-store" in response["Cache-Control"]
    assert client.post(url).status_code == 405
    path.write_bytes(b"corrupt synthetic artifact")
    assert client.get(url).status_code == 404
    path.unlink()
    assert client.get(url).status_code == 404
    assert client.get(url + "../../").status_code == 404
    assert client.get(reverse("generation_detail", args=[run.pk])).status_code == 200


@pytest.mark.parametrize("status", ["QUEUED", "RUNNING", "FAILED", "CANCELLED", "REVIEW_REQUIRED"])
def test_partial_cancelled_or_failed_batches_are_never_downloadable(
    resolver_inputs, settings, tmp_path, client, status
):
    run, artifact, _path, _data = completed(resolver_inputs, settings, tmp_path)
    import uuid

    from django.utils import timezone

    from apps.jobs.models import Job

    fields = {"status": status}
    if status == "RUNNING":
        fields.update(lease_owner=uuid.uuid4(), lease_expires_at=timezone.now(), started_at=timezone.now())
    Job.objects.filter(pk=run.job_id).update(**fields)
    client.force_login(resolver_inputs[0])
    assert client.get(reverse("generation_download", args=[artifact.pk])).status_code == 404
    response = client.get(reverse("generation_detail", args=[run.pk]))
    assert not response.context["complete"]


def test_artifact_receipt_inventory_and_database_guards(resolver_inputs, settings, tmp_path):
    run, artifact, _path, _data = completed(resolver_inputs, settings, tmp_path)
    assert g.is_complete(run)
    with pytest.raises(ValidationError):
        artifact.save()
    with pytest.raises(ValidationError):
        artifact.delete()
    with pytest.raises(IntegrityError), transaction.atomic(), connection.cursor() as cursor:
        cursor.execute("UPDATE exports_exportartifact SET sha256=%s WHERE id=%s", ["0" * 64, artifact.pk.hex])
    intent = artifact.intent
    intent.result = {"sha256": "0" * 64}
    intent.save()
    assert not g.is_complete(run)


def test_output_names_disarm_traversal_reserved_names_and_distinguish_people(resolver_inputs):
    run = authorize(**permission(resolver_inputs))
    person = {**run.snapshot.payload["participants"][0], "name": "../../CON:<script>"}
    path = g.output_path(run.snapshot, person)
    assert ".." not in path.split("/") and "<" not in path and ":" not in path
    import uuid

    assert g.output_path(run.snapshot, {**person, "id": str(uuid.uuid4())}) != path
