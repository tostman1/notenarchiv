"""Per-person stale classification, exact history integrity and secure targeted UI."""

import hashlib
from types import SimpleNamespace

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from apps.exports import archive_services, generation
from apps.exports import library_services as library
from apps.exports.models import ExportCompletion, ExportPublication, ExportStage
from apps.exports.snapshot_services import authorize
from apps.jobs.models import Job, OperationIntent
from apps.projects.models import PartOverride, ProjectParticipant, ProjectPosition
from apps.projects.preflight_services import build_report, fingerprint, report_token
from tests.pdf_fixtures import pdf
from tests.test_resolution import resolver_inputs as _fixture

resolver_inputs = _fixture


def synthetic_outputs(inputs, settings, tmp_path):
    actor, project, arr, parts, people, positions, first, second, *_ = inputs
    for person in people[1:]:
        for position in positions[:2]:
            PartOverride.objects.create(
                project=project,
                participant=person,
                position=position,
                desired_part=parts[1],
                edition=first.assignments.get(),
            )
    report = build_report(project.pk, participant_ids=[p.pk for p in people[1:]])
    run = authorize(
        project.pk,
        participant_ids=list(report.session.participants),
        position_ids=list(report.session.positions),
        token=report_token(report, actor),
        acknowledgements=sorted(report.missing_keys),
        actor=actor,
    )
    settings.EXPORT_DIR = tmp_path / "export"
    data_root = tmp_path / "data"
    data_root.mkdir(mode=0o700)
    settings.DIAGNOSTIC_LOG_DIR = data_root / "logs"
    artifacts = []
    for person in run.snapshot.payload["participants"]:
        path = generation.output_path(run.snapshot, person)
        publication = ExportPublication.objects.create(run=run, participant_id=person["id"], relative_path=path)
        data = pdf()
        stage = ExportStage.objects.create(
            publication=publication,
            attempt=1,
            sha256=hashlib.sha256(data).hexdigest(),
            byte_size=len(data),
            manifest={
                "snapshot_id": str(run.snapshot_id),
                "snapshot_sha256": run.snapshot.sha256,
                "participant_id": person["id"],
                "participant_name": person["name"],
                "page_count": 1,
            },
        )
        intent = OperationIntent.objects.create(
            job=run.job,
            attempt=1,
            key=generation.effect_key(publication),
            payload={"publication": str(publication.pk)},
            state="APPLIED",
            result=stage.receipt,
        )
        generation.acknowledge(SimpleNamespace(job_id=run.job_id), intent)
        file = settings.EXPORT_DIR / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(data)
        artifacts.append(run.artifacts.get(participant_id=person["id"]))
    inventory = generation.inventory(run)
    ExportCompletion.objects.create(run=run, inventory=inventory, sha256=fingerprint(inventory))
    Job.objects.filter(pk=run.job_id).update(status="SUCCEEDED")
    for artifact in artifacts:
        artifact.run.job.refresh_from_db()
    return run, artifacts


def test_one_person_part_change_marks_only_affected_output_stale_and_preserves_bytes(
    resolver_inputs, settings, tmp_path
):
    run, artifacts = synthetic_outputs(resolver_inputs, settings, tmp_path)
    before = {a.pk: (settings.EXPORT_DIR / a.relative_path).read_bytes() for a in artifacts}
    assert all(not library.classify(a).stale for a in artifacts)
    person = resolver_inputs[4][2]
    PartOverride.objects.filter(participant=person, position=resolver_inputs[5][0]).update(active=False)
    states = {a.participant_id: library.classify(a) for a in artifacts}
    assert states[person.pk].stale and "PART_ASSIGNMENT_CHANGED" in states[person.pk].stale_reasons
    assert not states[resolver_inputs[4][1].pk].stale
    assert all(s.reproducible and s.output == "VERIFIED" for s in states.values())
    assert all((settings.EXPORT_DIR / a.relative_path).read_bytes() == before[a.pk] for a in artifacts)


def test_piece_list_and_participant_removal_are_distinct_from_corrupt_output(resolver_inputs, settings, tmp_path):
    run, artifacts = synthetic_outputs(resolver_inputs, settings, tmp_path)
    ProjectPosition.objects.filter(pk=resolver_inputs[5][0].pk).update(arrangement=None)
    assert all("PIECE_LIST_CHANGED" in library.classify(a).stale_reasons for a in artifacts)
    ProjectParticipant.objects.filter(pk=artifacts[0].participant_id).update(active=False)
    assert "PARTICIPANT_REMOVED" in library.classify(artifacts[0]).stale_reasons
    (settings.EXPORT_DIR / artifacts[1].relative_path).write_bytes(b"Synthetic output corruption")
    state = library.classify(artifacts[1])
    assert state.output == "UNAVAILABLE" and state.reproducible


def test_new_archive_preference_does_not_override_explicit_personal_historical_choice(
    resolver_inputs, settings, tmp_path
):
    run, artifacts = synthetic_outputs(resolver_inputs, settings, tmp_path)
    from apps.archive.models import PreferredEdition

    PreferredEdition.objects.create(
        arrangement=resolver_inputs[2], part=resolver_inputs[3][1], assignment=resolver_inputs[7].assignments.get()
    )
    assert all(not library.classify(a).stale for a in artifacts)
    first = resolver_inputs[6]
    (settings.CURATED_DIR / first.relative_path).write_bytes(b"Corrupt exact historical input")
    state = library.classify(artifacts[0])
    assert state.output == "VERIFIED" and not state.reproducible and state.input_reasons == ("INPUT_UNAVAILABLE",)


def test_library_authenticated_filters_pagination_and_targeted_current_authorization(
    resolver_inputs, settings, tmp_path, client
):
    run, artifacts = synthetic_outputs(resolver_inputs, settings, tmp_path)
    url = reverse("export_library")
    assert client.get(url).status_code == 302
    client.force_login(resolver_inputs[0])
    response = client.get(
        url, {"project": str(run.snapshot.project_id), "participant": str(artifacts[0].participant_id)}
    )
    assert response.status_code == 200 and len(response.context["page"]) == 1
    assert b"Historisch exakt reproduzierbar" in response.content
    assert client.get(url, {"project": "../../secret"}).status_code == 404
    target = client.get(reverse("export_regenerate", args=[artifacts[0].pk]))
    assert target.status_code == 302 and "participants=" + str(artifacts[0].participant_id) in target["Location"]
    selected = client.get(target["Location"])
    assert selected.context["selection"].initial["participants"] == [str(artifacts[0].participant_id)]
    assert len(selected.context["selection"].initial["positions"]) == 3


def test_zip_requires_csrf_and_complete_exact_artifacts(resolver_inputs, settings, tmp_path, client):
    import zipfile
    from io import BytesIO

    from django.test import Client

    run, artifacts = synthetic_outputs(resolver_inputs, settings, tmp_path)
    url = reverse("export_batch_download")
    client.force_login(resolver_inputs[0])
    csrf = Client(enforce_csrf_checks=True)
    csrf.force_login(resolver_inputs[0])
    assert csrf.post(url, {"artifacts": [str(a.pk) for a in artifacts]}).status_code == 403
    response = client.post(url, {"artifacts": [str(a.pk) for a in artifacts]})
    assert response.status_code == 200
    with zipfile.ZipFile(BytesIO(b"".join(response.streaming_content))) as archive:
        assert len(archive.namelist()) == 2
    assert client.post(url, {"artifacts": [str(artifacts[0].pk)] * 2}).status_code == 400
    (settings.EXPORT_DIR / artifacts[0].relative_path).unlink()
    assert client.post(url, {"artifacts": [str(artifacts[0].pk)]}).status_code == 404


def test_generated_archive_reading_order_and_variant_are_bound_without_project(resolver_inputs):
    selected = archive_services.report([resolver_inputs[7].pk, resolver_inputs[6].pk])
    token = archive_services.token(selected, resolver_inputs[0], "READING")
    run = archive_services.authorize([f.pk for f in selected], token, resolver_inputs[0], variant="READING")
    assert run.snapshot.project_id is None and run.snapshot.payload["output_variant"] == "READING"
    assert [c["id"] for c in run.snapshot.payload["archive_files"]] == [str(f.pk) for f in selected]
    with pytest.raises(ValidationError):
        archive_services.authorize([f.pk for f in selected], token, resolver_inputs[0], variant="PRINT")


def test_targeted_print_variant_is_preflight_bound_and_no_reading_substitution(resolver_inputs):
    from apps.projects.models import Project

    Project.objects.filter(pk=resolver_inputs[1].pk).update(layout="REGULAR")
    actor, project, arr, parts, people, positions, first, *_ = resolver_inputs
    for position in positions[:2]:
        PartOverride.objects.create(
            project=project,
            participant=people[2],
            position=position,
            desired_part=parts[1],
            edition=first.assignments.get(),
        )
    report = build_report(project.pk, participant_ids=[people[2].pk])
    reading = report_token(report, actor)
    with pytest.raises(ValidationError):
        authorize(
            project.pk,
            participant_ids=[people[2].pk],
            position_ids=list(report.session.positions),
            token=reading,
            acknowledgements=[],
            actor=actor,
            variant="PRINT",
        )
    report.payload["output_variant"] = "PRINT"
    run = authorize(
        project.pk,
        participant_ids=[people[2].pk],
        position_ids=list(report.session.positions),
        token=report_token(report, actor),
        acknowledgements=[],
        actor=actor,
        variant="PRINT",
    )
    assert run.snapshot.payload["output_variant"] == "PRINT" and run.snapshot.participants.count() == 1


def test_download_cannot_cross_requested_project_scope(resolver_inputs, settings, tmp_path, client):
    import uuid

    run, artifacts = synthetic_outputs(resolver_inputs, settings, tmp_path)
    client.force_login(resolver_inputs[0])
    url = reverse("generation_download", args=[artifacts[0].pk])
    assert client.get(url, {"project": str(uuid.uuid4())}).status_code == 404
    response = client.get(url, {"project": str(run.snapshot.project_id)})
    assert response.status_code == 200
    response.close()


def test_effective_edition_and_catalog_changes_have_specific_stale_reasons(resolver_inputs, settings, tmp_path):
    run, artifacts = synthetic_outputs(resolver_inputs, settings, tmp_path)
    first_person = artifacts[0].participant_id
    PartOverride.objects.filter(participant_id=first_person, position=resolver_inputs[5][0]).update(
        edition=resolver_inputs[7].assignments.get()
    )
    state = library.classify(artifacts[0])
    assert "EDITION_CHANGED" in state.stale_reasons and state.reproducible
    assert not library.classify(artifacts[1]).stale
    from apps.catalog.models import InstrumentVariant

    InstrumentVariant.objects.filter(pk=resolver_inputs[3][1].instrument_id).update(name="Changed synthetic instrument")
    assert "CATALOG_CHANGED" in library.classify(artifacts[1]).stale_reasons


def test_removed_other_participant_does_not_mark_unaffected_person_stale(resolver_inputs, settings, tmp_path):
    run, artifacts = synthetic_outputs(resolver_inputs, settings, tmp_path)
    ProjectParticipant.objects.filter(pk=artifacts[0].participant_id).update(active=False)
    assert not library.classify(artifacts[1]).stale


def test_classification_is_read_only_and_partial_run_is_never_complete(resolver_inputs, settings, tmp_path):
    run, artifacts = synthetic_outputs(resolver_inputs, settings, tmp_path)
    old_payload = run.snapshot.payload
    Job.objects.filter(pk=run.job_id).update(status="FAILED")
    artifacts[0].run.job.refresh_from_db()
    assert library.classify(artifacts[0]).output == "INCOMPLETE"
    run.snapshot.refresh_from_db()
    assert run.snapshot.payload == old_payload


def test_classification_budget_never_labels_unchecked_bytes_verified(resolver_inputs, settings, tmp_path):
    import time

    run, artifacts = synthetic_outputs(resolver_inputs, settings, tmp_path)
    state = library.classify(artifacts[0], cache={"deadline": time.monotonic() - 1, "bytes": 0})
    assert state.output == "UNCHECKED" and state.stale_reasons == ("CLASSIFICATION_LIMIT",)


def test_source_presence_change_is_specific_but_clean_copy_remains_reproducible(resolver_inputs, settings, tmp_path):
    run, artifacts = synthetic_outputs(resolver_inputs, settings, tmp_path)
    from apps.archive.models import SourceFile

    SourceFile.objects.filter(pk=resolver_inputs[6].source_version.source_file_id).update(presence="MISSING")
    state = library.classify(artifacts[0])
    assert "SOURCE_PRESENCE_CHANGED" in state.stale_reasons and state.reproducible


def test_other_corrupted_batch_member_is_not_advertised_as_downloadable(resolver_inputs, settings, tmp_path):
    run, artifacts = synthetic_outputs(resolver_inputs, settings, tmp_path)
    (settings.EXPORT_DIR / artifacts[0].relative_path).write_bytes(b"Corrupt batch member")
    state = library.classify(artifacts[1])
    assert state.output == "BATCH_UNAVAILABLE" and state.reproducible


def test_role_change_only_marks_affected_person_and_preserves_exact_history(resolver_inputs, settings, tmp_path):
    run, artifacts = synthetic_outputs(resolver_inputs, settings, tmp_path)
    from apps.projects.models import ProjectRole

    role = ProjectRole.objects.create(project=resolver_inputs[1], code="synthetic-role", label="Synthetic role")
    ProjectParticipant.objects.filter(pk=artifacts[0].participant_id).update(role=role)
    assert "ROLE_OR_RULE_CHANGED" in library.classify(artifacts[0]).stale_reasons
    assert not library.classify(artifacts[1]).stale


def test_archiving_project_does_not_invalidate_unchanged_historical_output(resolver_inputs, settings, tmp_path):
    run, artifacts = synthetic_outputs(resolver_inputs, settings, tmp_path)
    from apps.projects.models import Project

    Project.objects.filter(pk=resolver_inputs[1].pk).update(status="ARCHIVED")
    assert all(not library.classify(a).stale and library.classify(a).output == "VERIFIED" for a in artifacts)
