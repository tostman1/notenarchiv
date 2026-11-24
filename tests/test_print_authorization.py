"""Print artifacts authorize exact immutable inputs; no re-resolution or printer."""

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from apps.exports import archive_services as a
from apps.exports import print_services as p
from apps.exports.models import GenerationSnapshot
from apps.exports.snapshot_services import authorize, load_pinned_inputs
from apps.jobs.models import Job
from tests.test_generation_snapshots import permission
from tests.test_resolution import resolver_inputs as _resolution_fixture

resolver_inputs = _resolution_fixture


def test_print_snapshot_pins_same_versions_after_project_change_and_replays_once(resolver_inputs, settings, tmp_path):
    from apps.projects.models import Project

    Project.objects.filter(pk=resolver_inputs[1].pk).update(layout="REGULAR")
    from tests.test_generation_downloads import completed

    old, artifact, path, data = completed(resolver_inputs, settings, tmp_path)
    from apps.projects.models import ProjectParticipant

    ProjectParticipant.objects.filter(pk=resolver_inputs[4][2].pk).update(default_part=resolver_inputs[3][0])
    token = p.token(old.snapshot, resolver_inputs[0])
    run = p.authorize_print(old.snapshot_id, token, resolver_inputs[0])
    assert run.snapshot.source_snapshot_id == old.snapshot_id and run.snapshot.payload["output_variant"] == "PRINT"
    assert [pin.archive_file_id for pin in load_pinned_inputs(run.snapshot_id)[1]] == [resolver_inputs[6].pk] * 2
    assert p.authorize_print(old.snapshot_id, token, resolver_inputs[0]).pk == run.pk


def test_print_authorization_requires_csrf_login_complete_source_and_valid_token(
    resolver_inputs, client, settings, tmp_path
):
    from apps.projects.models import Project

    Project.objects.filter(pk=resolver_inputs[1].pk).update(layout="REGULAR")
    from django.test import Client

    from tests.test_generation_downloads import completed

    old, artifact, path, data = completed(resolver_inputs, settings, tmp_path)
    Job.objects.filter(pk=old.job_id).update(status="QUEUED")
    url = reverse("generation_print", args=[old.pk])
    assert client.post(url).status_code == 302
    client.force_login(resolver_inputs[0])
    csrf = Client(enforce_csrf_checks=True)
    csrf.force_login(resolver_inputs[0])
    token = p.token(old.snapshot, resolver_inputs[0])
    assert csrf.post(url, {"token": token}).status_code == 403
    assert client.post(url, {"token": token}).status_code == 409
    Job.objects.filter(pk=old.job_id).update(status="SUCCEEDED")
    assert client.post(url, {"token": "forged"}).status_code == 409
    assert client.post(url, {"token": token}).status_code == 302


def test_archive_print_snapshot_has_real_pins_and_no_project_or_person(resolver_inputs):
    selected = a.report([resolver_inputs[6].pk, resolver_inputs[7].pk])
    run = a.authorize([f.pk for f in selected], a.token(selected, resolver_inputs[0]), resolver_inputs[0])
    assert run.snapshot.kind == "ARCHIVE_NOTES" and run.snapshot.project_id is None
    assert not run.snapshot.participants.exists() and not run.snapshot.positions.exists()
    snapshot, pins = load_pinned_inputs(run.snapshot_id)
    assert len(pins) == 2 and [pin.ordinal for pin in sorted(pins, key=lambda p: p.ordinal)] == [1, 2]
    assert all(pin.participant_id is None and pin.position_id is None for pin in pins)
    with pytest.raises(ValidationError):
        a.authorize([selected[0].pk], a.token(selected, resolver_inputs[0]), resolver_inputs[0])
    assert GenerationSnapshot.objects.count() == 1


def test_archive_print_rejects_unconfirmed_duplicate_and_changed_inputs(resolver_inputs, settings):
    first = resolver_inputs[6]
    selected = a.report([first.pk])
    token = a.token(selected, resolver_inputs[0])
    (settings.CURATED_DIR / first.relative_path).write_bytes(b"Corrupt synthetic source")
    with pytest.raises(ValidationError):
        a.authorize([first.pk], token, resolver_inputs[0])
    with pytest.raises(ValidationError):
        a.report([first.pk, first.pk])


def test_print_rejects_marchbook_and_corrupt_exact_source_without_substitution(resolver_inputs, settings):
    old = authorize(**permission(resolver_inputs))
    Job.objects.filter(pk=old.job_id).update(status="SUCCEEDED")
    with pytest.raises(ValidationError):
        p.authorize_print(old.snapshot_id, p.token(old.snapshot, resolver_inputs[0]), resolver_inputs[0])
    first = resolver_inputs[6]
    (settings.CURATED_DIR / first.relative_path).write_bytes(b"Corrupt exact print source")
    with pytest.raises(ValidationError):
        p.authorize_print(old.snapshot_id, p.token(old.snapshot, resolver_inputs[0]), resolver_inputs[0])


def test_preview_requires_login_and_completed_verified_artifact(resolver_inputs, settings, tmp_path, client):
    from tests.test_generation_downloads import completed

    run, artifact, path, data = completed(resolver_inputs, settings, tmp_path)
    url = reverse("generation_preview", args=[artifact.pk])
    assert client.get(url).status_code == 302
    client.force_login(resolver_inputs[0])
    response = client.get(url)
    assert response.status_code == 200 and b"archive/preview.mjs" in response.content
    assert "frame-ancestors 'none'" in response["Content-Security-Policy"]
    assert client.post(url).status_code == 405
    path.write_bytes(b"Corrupt synthetic artifact")
    assert client.get(url).status_code == 404
