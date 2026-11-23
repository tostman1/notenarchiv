"""Current excerpt, replacement, exact historical pins and independent contents."""

import uuid
from io import BytesIO

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse
from pypdf import PdfReader

from apps.exports import selection_services as s
from apps.exports.generation import personal_pieces
from apps.exports.models import GenerationSnapshot
from apps.exports.snapshot_services import authorize, load_pinned_inputs
from apps.projects.models import PartOverride, ProjectParticipant, ProjectPosition
from apps.projects.preflight_services import build_report, report_token
from core.pdf import Processor
from tests.test_generation_snapshots import permission
from tests.test_resolution import resolver_inputs as _resolution_fixture

resolver_inputs = _resolution_fixture


def excerpt(inputs, people, positions):
    actor, project, *_ = inputs
    report = build_report(project.pk, participant_ids=people, position_ids=positions)
    return authorize(
        project.pk,
        participant_ids=people,
        position_ids=positions,
        token=report_token(report, actor),
        acknowledgements=sorted(report.missing_keys),
        actor=actor,
        kind="EXCERPT",
    )


def test_one_position_one_person_uses_exact_override_without_contents(resolver_inputs, tmp_path):
    values = permission(resolver_inputs)
    run = excerpt(resolver_inputs, values["participant_ids"], values["position_ids"][:1])
    snapshot, pins = load_pinned_inputs(run.snapshot_id)
    pieces = personal_pieces(snapshot, pins, run.snapshot.participants.get().participant_id)
    reader = PdfReader(BytesIO(Processor(tmp_path).compose(pieces, project="Synthetic", contents=False)))
    assert len(reader.pages) == 1 and pins[0].part_id == resolver_inputs[3][1].pk
    assert pins[0].archive_file_id == resolver_inputs[6].pk
    assert "Inhaltsverzeichnis" not in reader.pages[0].extract_text()
    assert ProjectPosition.objects.filter(project=resolver_inputs[1], active=True).count() == 3


def test_multiple_positions_people_and_distinct_parts_remain_exact(resolver_inputs):
    actor, project, arr, parts, people, positions, first, second, make = resolver_inputs
    third = make(3, part=parts[2])
    for person, part, file in ((people[0], parts[1], first), (people[2], parts[2], third)):
        for position in positions[:2]:
            PartOverride.objects.create(
                project=project,
                participant=person,
                position=position,
                desired_part=part,
                edition=file.assignments.get(),
            )
    before = list(project.positions.values_list("pk", "order", "arrangement_id"))
    run = excerpt(resolver_inputs, [people[0].pk, people[2].pk], [positions[0].pk, positions[1].pk])
    assert run.snapshot.inputs.count() == 4
    assert set(run.snapshot.inputs.values_list("part_id", flat=True)) == {parts[1].pk, parts[2].pk}
    assert before == list(project.positions.values_list("pk", "order", "arrangement_id"))


def test_replacement_at_slot_preserves_number_and_uses_new_arrangement(resolver_inputs):
    actor, project, arr, parts, people, positions, first, second, make = resolver_inputs
    from apps.catalog.models import Arrangement

    new = Arrangement.objects.create(work=arr.work, edition="Synthetic replacement")
    file = make(3, owner=new, part=parts[1])
    ProjectPosition.objects.filter(pk=positions[0].pk).update(arrangement=new)
    run = excerpt(resolver_inputs, [people[1].pk], [positions[0].pk])
    assert run.snapshot.positions.get().number == 1
    assert run.snapshot.inputs.get().archive_file_id == file.pk
    assert run.snapshot.positions.get().position_id == positions[0].pk


def test_historical_exact_reprint_ignores_changed_defaults_and_removed_positions(resolver_inputs):
    old = authorize(**permission(resolver_inputs))
    person = old.snapshot.participants.get()
    ProjectParticipant.objects.filter(pk=person.participant_id).update(default_part=resolver_inputs[3][0], active=False)
    ProjectPosition.objects.filter(pk=resolver_inputs[5][0].pk).update(arrangement=None, active=False, order=None)
    report = s.historical_report(old.snapshot_id, [person.participant_id], [resolver_inputs[5][0].pk])
    token = s.selection_token(report, resolver_inputs[0])
    run = s.authorize_selection(report, token, [], resolver_inputs[0])
    assert run.snapshot.source_snapshot_id == old.snapshot_id
    assert run.snapshot.inputs.get().archive_file_id == resolver_inputs[6].pk
    assert run.snapshot.inputs.get().part_id == resolver_inputs[3][1].pk
    assert s.authorize_selection(report, token, [], resolver_inputs[0]).pk == run.pk
    assert load_pinned_inputs(run.snapshot_id)[0].positions.get().number == 1


def test_contents_only_has_no_people_music_or_ack_dependency(resolver_inputs, tmp_path):
    report = s.contents_report(resolver_inputs[1].pk)
    run = s.authorize_selection(report, s.selection_token(report, resolver_inputs[0]), [], resolver_inputs[0])
    assert (
        run.snapshot.kind == "CONTENTS" and not run.snapshot.participants.exists() and not run.snapshot.inputs.exists()
    )
    load_pinned_inputs(run.snapshot_id)
    pieces = [
        {
            "number": p["order"],
            "title": p["title"],
            "state": "RESERVE" if p["arrangement"] == "None" else "CONTENTS",
            "data": None,
        }
        for p in report.payload["positions"]
    ]
    reader = PdfReader(
        BytesIO(Processor(tmp_path).compose(pieces, project=report.payload["project_name"], music=False))
    )
    assert len(reader.pages) == 1 and "Reserve" in reader.pages[0].extract_text()
    assert "Noten fehlen" not in reader.pages[0].extract_text()


def test_selection_auth_csrf_stale_tokens_and_foreign_history(resolver_inputs, client):
    from django.test import Client

    actor, project, *_ = resolver_inputs
    url = reverse("project_contents_export", args=[project.pk])
    assert client.get(url).status_code == 302
    client.force_login(actor)
    response = client.get(url)
    token = response.context["token"]
    csrf = Client(enforce_csrf_checks=True)
    csrf.force_login(actor)
    assert csrf.post(url, {"token": token}).status_code == 403
    ProjectPosition.objects.filter(pk=resolver_inputs[5][0].pk).update(arrangement=None)
    assert client.post(url, {"token": token}).status_code == 409
    assert not GenerationSnapshot.objects.exists()
    old = authorize(**permission(resolver_inputs, missing=True))
    with pytest.raises(ValidationError):
        s.historical_report(old.snapshot_id, [uuid.uuid4()], [resolver_inputs[5][1].pk])


def test_excerpt_reserves_missing_and_unconfirmed_fail_closed(resolver_inputs, tmp_path):
    actor, project, arr, parts, people, positions, first, second, make = resolver_inputs
    with pytest.raises(ValidationError, match="Reserven"):
        excerpt(resolver_inputs, [people[0].pk], [positions[2].pk])
    run = excerpt(resolver_inputs, [people[0].pk], [positions[0].pk])
    snapshot, pins = load_pinned_inputs(run.snapshot_id)
    data = Processor(tmp_path).compose(
        personal_pieces(snapshot, pins, people[0].pk), project="Synthetic", contents=False
    )
    assert "Noten fehlen" in PdfReader(BytesIO(data)).pages[0].extract_text()
    pending = make(4, part=parts[0], confirmed=False)
    invalid = PartOverride.objects.create(
        project=project,
        position=positions[1],
        participant=people[0],
        desired_part=parts[1],
        edition=first.assignments.get(),
    )
    # Simulate legacy invalid metadata; the generation gate must still reject it.
    PartOverride.objects.filter(pk=invalid.pk).update(desired_part=parts[0])
    with pytest.raises(ValidationError):
        excerpt(resolver_inputs, [people[0].pk], [positions[1].pk])
    assert pending.review_state != "CONFIRMED"


def test_historical_reprint_requires_new_missing_ack_and_exact_uncorrupted_bytes(resolver_inputs, settings):
    old = authorize(**permission(resolver_inputs, missing=True))
    person = old.snapshot.participants.get()
    report = s.historical_report(old.snapshot_id, [person.participant_id], [resolver_inputs[5][0].pk])
    token = s.selection_token(report, resolver_inputs[0])
    with pytest.raises(ValidationError):
        s.authorize_selection(report, token, [], resolver_inputs[0])
    assert (
        s.authorize_selection(report, token, report.missing, resolver_inputs[0]).snapshot.acknowledgements
        == report.missing
    )


def test_excerpt_endpoint_requires_login_csrf_and_fresh_scope(resolver_inputs, client):
    from django.test import Client

    values = permission(resolver_inputs)
    url = reverse("project_excerpt", args=[values["project_id"]])
    payload = {
        "action": "authorize",
        "participants": [str(v) for v in values["participant_ids"]],
        "positions": [str(values["position_ids"][0])],
        "token": values["token"],
    }
    assert client.get(url).status_code == 302
    csrf = Client(enforce_csrf_checks=True)
    csrf.force_login(values["actor"])
    assert csrf.post(url, payload).status_code == 403
    client.force_login(values["actor"])
    assert client.post(url, payload).status_code == 409
    assert not GenerationSnapshot.objects.exists()


def test_historical_exact_edition_corruption_is_not_replaced(resolver_inputs, settings):
    old = authorize(**permission(resolver_inputs))
    first = resolver_inputs[6]
    (settings.CURATED_DIR / first.relative_path).write_bytes(b"Corrupt synthetic historical edition")
    with pytest.raises(ValidationError):
        s.historical_report(old.snapshot_id, [resolver_inputs[4][2].pk], [resolver_inputs[5][0].pk])
    assert GenerationSnapshot.objects.count() == 1


def test_historical_endpoint_requires_csrf_and_selected_snapshot_identity(resolver_inputs, client):
    from django.test import Client

    old = authorize(**permission(resolver_inputs))
    url = reverse("historical_excerpt", args=[old.snapshot_id])
    assert client.get(url).status_code == 302
    client.force_login(resolver_inputs[0])
    values = {
        "participants": [str(resolver_inputs[4][2].pk)],
        "positions": [str(resolver_inputs[5][0].pk)],
        "action": "inspect",
    }
    csrf = Client(enforce_csrf_checks=True)
    csrf.force_login(resolver_inputs[0])
    assert csrf.post(url, values).status_code == 403
    response = client.post(url, values)
    assert response.status_code == 200
    token = response.context["token"]
    assert client.post(url, {**values, "action": "authorize", "token": "forged"}).status_code == 409
    response = client.post(url, {**values, "action": "authorize", "token": token})
    assert response.status_code == 302 and GenerationSnapshot.objects.count() == 2


def test_excerpt_uses_explicit_old_edition_even_when_another_is_available(resolver_inputs):
    values = permission(resolver_inputs)
    from apps.archive.models import PreferredEdition

    PreferredEdition.objects.create(
        arrangement=resolver_inputs[2], part=resolver_inputs[3][1], assignment=resolver_inputs[7].assignments.get()
    )
    run = excerpt(resolver_inputs, values["participant_ids"], values["position_ids"][:1])
    assert run.snapshot.inputs.get().archive_file_id == resolver_inputs[6].pk


def test_historical_selection_does_not_require_unrequested_corrupt_editions(resolver_inputs, settings):
    actor, project, arr, parts, people, positions, first, second, make = resolver_inputs
    for person, file in ((people[1], first), (people[2], second)):
        for position in positions[:2]:
            PartOverride.objects.create(
                project=project,
                position=position,
                participant=person,
                desired_part=parts[1],
                edition=file.assignments.get(),
            )
    old = excerpt(resolver_inputs, [people[1].pk, people[2].pk], [positions[0].pk, positions[1].pk])
    (settings.CURATED_DIR / second.relative_path).write_bytes(b"Unrequested synthetic corrupt edition")
    report = s.historical_report(old.snapshot_id, [people[1].pk], [positions[0].pk])
    run = s.authorize_selection(report, s.selection_token(report, actor), [], actor)
    assert load_pinned_inputs(run.snapshot_id)[1][0].archive_file_id == first.pk


def test_contents_export_still_works_with_no_active_people_and_corrupt_music(resolver_inputs, settings):
    actor, project, *_ = resolver_inputs
    ProjectParticipant.objects.filter(project=project).update(active=False)
    (settings.CURATED_DIR / resolver_inputs[6].relative_path).write_bytes(b"Unavailable unrelated synthetic music")
    report = s.contents_report(project.pk)
    run = s.authorize_selection(report, s.selection_token(report, actor), [], actor)
    assert run.snapshot.kind == "CONTENTS" and run.snapshot.positions.count() == 3


def test_migration_refresh_retains_snapshot_and_artifact_update_guards(resolver_inputs):
    from django.db import IntegrityError, connection, transaction

    old = authorize(**permission(resolver_inputs))
    with pytest.raises(IntegrityError), transaction.atomic(), connection.cursor() as cursor:
        cursor.execute("UPDATE exports_generationsnapshot SET kind='CONTENTS' WHERE id=%s", [old.snapshot_id.hex])
    with connection.cursor() as cursor:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='trigger'")
        names = {row[0] for row in cursor.fetchall()}
    assert {
        "exports_exportartifact_update_guard",
        "exports_exportpublication_update_guard",
        "archive_archivefile_pin_guard",
        "exports_snapshotparticipant_update_guard",
    } <= names
