"""Durable isolated project graph, optimistic revisions and full clone mapping."""

import uuid

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import Client
from django.urls import reverse

from apps.catalog.models import Part
from apps.members.models import Member
from apps.projects import models as m
from apps.projects import services as s


def values(name="Synthetic project"):
    return {
        "name": name,
        "layout": "MARCHBOOK",
        "width_mm": 170,
        "height_mm": 120,
        "cover_enabled": True,
        "cover_title": "Synthetic cover",
    }


@pytest.fixture
def project_inputs(db, edition_inputs):
    actor, arrangement, parts, first, *_ = edition_inputs
    project = s.save_project(values(), actor=actor)
    role = m.ProjectRole.objects.create(project=project, code="3", label="Musical role")
    positions = [
        m.ProjectPosition.objects.create(project=project, order=i, arrangement=arrangement if i != 2 else None)
        for i in (1, 2, 3)
    ]
    member = Member.objects.create(name="Synthetic musician", regular_part=parts[0])
    participants = [
        m.ProjectParticipant.objects.create(
            project=project, member=member, display_name=member.name, default_part=parts[0], role=role
        ),
        m.ProjectParticipant.objects.create(
            project=project, guest_id=uuid.uuid4(), display_name="Synthetic guest", default_part=parts[0]
        ),
    ]
    edition = first.assignments.get()
    m.PartOverride.objects.create(
        project=project, participant=participants[0], position=positions[0], desired_part=parts[0], edition=edition
    )
    m.ProjectEditionPreference.objects.create(project=project, arrangement=arrangement, part=parts[0], edition=edition)
    m.PositionEditionPreference.objects.create(project=project, position=positions[0], part=parts[0], edition=edition)
    m.EnsembleMapping.objects.create(project=project, role=role, instrument=parts[0].instrument, part=parts[0])
    m.EnsembleMapping.objects.create(
        project=project, role=role, instrument=parts[0].instrument, part=parts[0], position=positions[0]
    )
    replacement = Part.objects.create(instrument=parts[0].instrument, code="3")
    m.ReplacementRule.objects.create(project=project, desired_part=parts[0], replacement_part=replacement)
    m.ReplacementRule.objects.create(
        project=project, desired_part=parts[0], replacement_part=replacement, position=positions[0]
    )
    return actor, project, arrangement, parts, positions, participants, role, edition


def test_same_title_crud_revision_archive_and_retained_ids(project_inputs):
    actor, project, *_ = project_inputs
    other = s.save_project(values(), actor=actor)
    assert other.pk != project.pk and other.name == project.name
    saved = s.save_project(values("Changed synthetic"), actor=actor, project_id=project.pk, expected_revision=1)
    assert saved.pk == project.pk and saved.revision == 2
    with pytest.raises(s.ProjectConflict):
        s.save_project(values(), actor=actor, project_id=project.pk, expected_revision=1)
    archived = s.archive_project(project.pk, actor=actor, expected_revision=2)
    assert archived.status == "ARCHIVED" and archived.positions.count() == 3
    with pytest.raises(s.ProjectConflict):
        s.save_project(values(), actor=actor, project_id=project.pk, expected_revision=3)
    s.archive_project(project.pk, actor=actor, expected_revision=3, archived=False)
    assert project.history.count() == 4
    with pytest.raises(ValidationError):
        project.delete()


def test_duplicate_remaps_every_project_identity_and_preserves_shared_catalog(project_inputs):
    actor, project, _arr, _parts, positions, participants, _role, edition = project_inputs
    clone = s.duplicate_project(project.pk, name=project.name, actor=actor, expected_revision=1)
    project.refresh_from_db()
    assert project.revision == 1 and clone.duplicated_from_id == project.pk
    assert clone.positions.count() == 3 and clone.participants.count() == 2
    assert not set(clone.positions.values_list("pk", flat=True)) & {item.pk for item in positions}
    assert not set(clone.participants.values_list("pk", flat=True)) & {item.pk for item in participants}
    assert clone.positions.get(order=2).arrangement_id is None
    for model, records in s.graph_rows(clone).items():
        assert len(records) == model.objects.filter(project=project).count()
        for row in records:
            for field in row._meta.fields:
                if field.is_relation and field.related_model in {
                    m.ProjectPosition,
                    m.ProjectParticipant,
                    m.ProjectRole,
                }:
                    target = getattr(row, field.name)
                    assert target is None or target.project_id == clone.pk
    override = m.PartOverride.objects.get(project=clone)
    assert override.edition_id == edition.pk
    guest = clone.participants.get(member__isnull=True)
    assert guest.guest_id != participants[1].guest_id
    s.save_project(values("Clone changed"), actor=actor, project_id=clone.pk, expected_revision=1)
    project.refresh_from_db()
    assert project.name == "Synthetic project"


def test_cross_project_references_rejected_transactionally(project_inputs):
    actor, project, arr, parts, positions, participants, role, edition = project_inputs
    other = s.save_project(values("Other"), actor=actor)
    foreign = m.ProjectPosition.objects.create(project=other, order=1, arrangement=arr)
    records = [
        m.PartOverride(project=project, participant=participants[1], position=foreign, desired_part=parts[0]),
        m.PositionEditionPreference(project=project, position=foreign, part=parts[0], edition=edition),
        m.EnsembleMapping(project=other, role=role, instrument=parts[0].instrument, part=parts[0]),
    ]
    for record in records:
        with pytest.raises(ValidationError):
            s.save_associated(record, actor=actor, expected_revision=1)
    project.refresh_from_db()
    other.refresh_from_db()
    assert project.revision == other.revision == 1
    with pytest.raises(ValidationError):
        m.PartOverride.objects.create(
            project=project, participant=participants[1], position=positions[1], desired_part=parts[0]
        )


def test_sqlite_unique_scopes_and_identity_constraints(project_inputs):
    _actor, project, _arr, parts, positions, participants, role, _edition = project_inputs
    for model, data in [
        (m.ProjectPosition, {"project": project, "order": 1}),
        (
            m.ProjectParticipant,
            {"project": project, "member": participants[0].member, "display_name": "Other", "default_part": parts[0]},
        ),
        (m.ProjectParticipant, {"project": project, "display_name": "No identity", "default_part": parts[0]}),
        (m.EnsembleMapping, {"project": project, "role": role, "instrument": parts[0].instrument, "part": parts[0]}),
    ]:
        with pytest.raises(IntegrityError), transaction.atomic():
            model.objects.bulk_create([model(**data)])
    assert project.positions.count() == 3
    with pytest.raises(ValidationError):
        project.history.first().save()


def test_project_auth_csrf_escape_and_conflict_ui(project_inputs, client):
    actor, project, *_ = project_inputs
    assert client.get(reverse("project_list")).status_code == 302
    client.force_login(actor)
    assert client.get(reverse("project_detail", args=[project.pk])).status_code == 200
    payload = {**values("<script>Synthetic</script>"), "expected_revision": 1}
    assert client.post(reverse("project_edit", args=[project.pk]), payload).status_code == 302
    assert client.post(reverse("project_edit", args=[project.pk]), payload).status_code == 409
    assert "&lt;script&gt;" in client.get(reverse("project_detail", args=[project.pk])).content.decode()
    csrf = Client(enforce_csrf_checks=True)
    csrf.force_login(actor)
    assert csrf.post(reverse("project_archive", args=[project.pk]), {"expected_revision": 2}).status_code == 403
    assert client.get(reverse("project_duplicate", args=[project.pk])).status_code == 405
    assert (
        client.post(
            reverse("project_duplicate", args=[project.pk]), {"name": "Copy", "expected_revision": 2}
        ).status_code
        == 302
    )


def test_project_validation_and_pinned_withdrawn_clone(project_inputs):
    actor, project, _arr, parts, _positions, _participants, _role, edition = project_inputs
    for bad in ({**values(), "name": " "}, {**values(), "width_mm": 0}):
        with pytest.raises(ValidationError):
            s.save_project(bad, actor=actor)
    from apps.archive.services import withdraw

    file = edition.archive_file
    withdraw(file.pk, actor=actor, expected_revision=file.revision)
    clone = s.duplicate_project(project.pk, name="Historical pinned copy", actor=actor, expected_revision=1)
    assert m.PartOverride.objects.get(project=clone).edition_id == edition.pk
    with pytest.raises(ValidationError):
        m.ProjectEditionPreference.objects.create(
            project=clone, arrangement=project.positions.get(order=1).arrangement, part=parts[0], edition=edition
        )


def test_mapping_incompatibility_cycles_and_stale_duplicate(project_inputs):
    actor, project, arr, parts, positions, participants, role, edition = project_inputs
    with pytest.raises(ValidationError):
        m.EnsembleMapping.objects.create(project=project, role=role, instrument=parts[1].instrument, part=parts[0])
    with pytest.raises(ValidationError):
        m.PartOverride.objects.create(
            project=project, participant=participants[1], position=positions[0], desired_part=parts[1], edition=edition
        )
    target = m.ReplacementRule.objects.filter(project=project, position__isnull=True).get().replacement_part
    with pytest.raises(ValidationError):
        m.ReplacementRule.objects.create(project=project, desired_part=target, replacement_part=parts[0])
    s.save_project(values(), actor=actor, project_id=project.pk, expected_revision=1)
    with pytest.raises(s.ProjectConflict):
        s.duplicate_project(project.pk, name="Stale", actor=actor, expected_revision=1)
    assert m.Project.objects.count() == 1


def test_new_revalidation_cannot_bypass_compatibility_and_scope_cannot_retarget(project_inputs):
    actor, project, _arr, parts, positions, participants, _role, _edition = project_inputs
    record = m.PartOverride(
        project=project,
        participant=participants[1],
        position=positions[1],
        desired_part=parts[0],
        needs_revalidation=True,
    )
    with pytest.raises(ValidationError):
        s.save_associated(record, actor=actor, expected_revision=1)
    previous = m.PartOverride.objects.get(project=project)
    previous.position = positions[2]
    with pytest.raises(ValidationError):
        s.save_associated(previous, actor=actor, expected_revision=1)
    project.refresh_from_db()
    assert project.revision == 1


def test_project_filters_pagination_and_archived_duplicate(project_inputs, client):
    actor, project, *_ = project_inputs
    client.force_login(actor)
    for n in range(26):
        s.save_project(values(f"Synthetic {n}"), actor=actor)
    response = client.get(reverse("project_list"), {"q": "synthetic", "status": "ACTIVE", "page": 2})
    assert response.status_code == 200 and len(response.context["page"]) == 2
    assert "q=synthetic" in response.context["filters"]
    assert client.get(reverse("project_list"), {"status": "invalid"}).status_code == 400
    archived = s.archive_project(project.pk, actor=actor, expected_revision=1)
    copy = s.duplicate_project(project.pk, name="Archived copy", actor=actor, expected_revision=archived.revision)
    assert copy.status == "ACTIVE" and copy.positions.count() == 3


def test_invalid_actor_clone_fails_atomically_and_source_remains(project_inputs):
    actor, project, *_ = project_inputs
    actor.is_active = False
    actor.save()
    with pytest.raises(ValidationError):
        s.duplicate_project(project.pk, name="Denied", actor=actor, expected_revision=1)
    assert m.Project.objects.count() == 1
    project.refresh_from_db()
    assert project.revision == 1
