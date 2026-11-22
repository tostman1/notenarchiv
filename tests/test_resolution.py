"""Single resolver precedence, exact inputs, no guessing and read-only provenance."""

import uuid

import pytest
from django.core.exceptions import ValidationError

from apps.archive import edition_services
from apps.archive import models as archive
from apps.archive import services as review
from apps.catalog.models import Part
from apps.projects import ensemble_services, rule_services
from apps.projects import models as m
from apps.projects import resolution_services as r
from apps.projects.services import save_project
from tests.test_projects import values


def revision(project):
    project.refresh_from_db()
    return project.revision


@pytest.fixture
def resolver_inputs(edition_inputs):
    actor, arrangement, variants, first, second, make = edition_inputs
    m.GlobalRuleState.objects.get_or_create(pk=1)
    project = save_project(values(), actor=actor)
    part1 = Part.objects.create(instrument=variants[0].instrument, code="1")
    part3 = Part.objects.create(instrument=variants[0].instrument, code="3")
    people = [
        m.ProjectParticipant.objects.create(
            project=project, guest_id=uuid.uuid4(), display_name=name, default_part=part
        )
        for name, part in [("Mathias", part1), ("Sebi", variants[0]), ("Riccardo", part3)]
    ]
    positions = [
        m.ProjectPosition.objects.create(project=project, order=n, arrangement=arrangement if n != 3 else None)
        for n in (1, 2, 3)
    ]
    return actor, project, arrangement, [part1, variants[0], part3, variants[1]], people, positions, first, second, make


def resolve(inputs, person=1, position=0):
    return r.resolve_cell(inputs[1].pk, inputs[5][position].pk, inputs[4][person].pk)


def test_saved_default_is_not_live_member_data_and_ambiguous_is_explicit(resolver_inputs):
    _actor, project, arr, parts, people, positions, first, _second, _make = resolver_inputs
    result = resolve(resolver_inputs)
    assert result.status == "AMBIGUOUS" and result.part_origin == "SAVED_DEFAULT"
    assert result.desired_part_id == parts[1].pk and result.assignment_id is None
    assert resolve(resolver_inputs, person=0).status == "MISSING"
    assert resolve(resolver_inputs, person=2).desired_part_id == parts[2].pk
    assert resolve(resolver_inputs, position=2).status == "RESERVE"
    assert project.revision == 1 and project.history.count() == 1


def test_personal_manual_part_two_wins_even_when_part_three_exists(resolver_inputs):
    actor, project, arr, parts, people, positions, first, _second, make = resolver_inputs
    make(3, part=parts[2])
    choice = first.assignments.get()
    override = m.PartOverride.objects.create(
        project=project, participant=people[2], position=positions[0], desired_part=parts[1], edition=choice
    )
    result = resolve(resolver_inputs, person=2)
    assert result.usable and result.part_origin == "PERSONAL" and result.edition_origin == "PERSONAL"
    assert result.desired_part_id == result.effective_part_id == parts[1].pk
    assert result.override_id == override.pk and result.assignment_id == choice.pk and result.file_id == first.pk
    assert result.sha256 == first.sha256 and result.source_version_id == first.source_version_id
    assert result.rule_id is None and result.project_revision == 1


def test_exact_edition_priority_personal_position_project_archive_sole(resolver_inputs):
    actor, project, arr, parts, people, positions, first, second, make = resolver_inputs
    first_id, second_id = first.assignments.get().pk, second.assignments.get().pk
    arr.refresh_from_db()
    edition_services.set_preference(arr.pk, parts[1].pk, first_id, actor=actor, expected_revision=arr.revision)
    assert resolve(resolver_inputs).edition_origin == "ARCHIVE"
    project_pref = rule_services.set_edition(
        project.pk,
        arrangement_id=arr.pk,
        part_id=parts[1].pk,
        edition_id=second_id,
        actor=actor,
        expected_revision=revision(project),
    )
    assert resolve(resolver_inputs).assignment_id == second_id and resolve(resolver_inputs).edition_origin == "PROJECT"
    pos_pref = rule_services.set_edition(
        project.pk,
        arrangement_id=arr.pk,
        part_id=parts[1].pk,
        edition_id=first_id,
        position_id=positions[0].pk,
        actor=actor,
        expected_revision=revision(project),
    )
    assert resolve(resolver_inputs).assignment_id == first_id and resolve(resolver_inputs).edition_origin == "POSITION"
    m.PartOverride.objects.create(
        project=project, position=positions[0], participant=people[1], desired_part=parts[1], edition_id=second_id
    )
    assert resolve(resolver_inputs).assignment_id == second_id and resolve(resolver_inputs).edition_origin == "PERSONAL"
    sole = make(3, part=parts[0])
    assert resolve(resolver_inputs, person=0).edition_origin == "SOLE"
    assert resolve(resolver_inputs, person=0).assignment_id == sole.assignments.get().pk
    assert resolve(resolver_inputs, position=1).preference_id == project_pref.pk and pos_pref.pk != project_pref.pk


@pytest.mark.parametrize("source", ["personal", "position", "project", "archive"])
def test_withdrawn_explicit_or_preferred_edition_never_substituted(resolver_inputs, source):
    actor, project, arr, parts, people, positions, first, second, make = resolver_inputs
    selected = first.assignments.get()
    if source == "personal":
        m.PartOverride.objects.create(
            project=project, position=positions[0], participant=people[1], desired_part=parts[1], edition=selected
        )
    elif source in {"position", "project"}:
        rule_services.set_edition(
            project.pk,
            arrangement_id=arr.pk,
            part_id=parts[1].pk,
            edition_id=selected.pk,
            position_id=positions[0].pk if source == "position" else None,
            actor=actor,
            expected_revision=revision(project),
        )
    else:
        edition_services.set_preference(arr.pk, parts[1].pk, selected.pk, actor=actor, expected_revision=arr.revision)
    make(3, part=parts[0])
    rule_services.save_replacement(
        project_id=project.pk,
        desired_part_id=parts[1].pk,
        replacement_part_id=parts[0].pk,
        actor=actor,
        expected_revision=revision(project),
    )
    review.withdraw(first.pk, actor=actor, expected_revision=first.revision)
    result = resolve(resolver_inputs)
    assert result.status == "INVALID" and result.assignment_id is None and result.rule_id is None
    assert result.edition_origin == source.upper()
    assert "EXPLICIT_EDITION_UNAVAILABLE" in result.reasons
    assert archive.ArchiveFile.objects.filter(pk=second.pk).exists()


def test_missing_desired_part_explicit_replacement_only_one_hop(resolver_inputs):
    actor, project, arr, parts, people, positions, first, _second, _make = resolver_inputs
    arr.refresh_from_db()
    edition_services.set_preference(
        arr.pk, parts[1].pk, first.assignments.get().pk, actor=actor, expected_revision=arr.revision
    )
    global_ = rule_services.save_replacement(
        desired_part_id=parts[2].pk, replacement_part_id=parts[1].pk, actor=actor, expected_revision=1
    )
    result = resolve(resolver_inputs, person=2)
    assert result.status == "SUBSTITUTED" and result.replacement_origin == "GLOBAL" and result.rule_id == global_.pk
    assert result.desired_part_id == parts[2].pk and result.effective_part_id == parts[1].pk
    assert result.part_origin == "SAVED_DEFAULT" and result.edition_origin == "ARCHIVE"
    project_rule = rule_services.save_replacement(
        project_id=project.pk,
        desired_part_id=parts[2].pk,
        replacement_part_id=parts[0].pk,
        actor=actor,
        expected_revision=revision(project),
    )
    rule_services.save_replacement(
        project_id=project.pk,
        desired_part_id=parts[0].pk,
        replacement_part_id=parts[1].pk,
        actor=actor,
        expected_revision=revision(project),
    )
    result = resolve(resolver_inputs, person=2)
    assert result.status == "MISSING" and result.effective_part_id == parts[0].pk and result.rule_id == project_rule.pk
    assert result.assignment_id is None  # never follows the available second hop


def test_ambiguity_does_not_trigger_replacement(resolver_inputs):
    actor, project, _arr, parts, _people, _positions, _first, _second, make = resolver_inputs
    make(3, part=parts[0])
    rule_services.save_replacement(
        project_id=project.pk,
        desired_part_id=parts[1].pk,
        replacement_part_id=parts[0].pk,
        actor=actor,
        expected_revision=revision(project),
    )
    result = resolve(resolver_inputs)
    assert result.status == "AMBIGUOUS" and result.rule_id is None and result.effective_part_id == parts[1].pk


def test_role_mapping_uses_saved_variant_and_personal_override_bypasses_role(resolver_inputs):
    actor, project, arr, parts, people, positions, first, _second, make = resolver_inputs
    role = ensemble_services.save_role(project.pk, code="3", label="Musical role", actor=actor, expected_revision=1)
    ensemble_services.assign_role(project.pk, people[2].pk, role.pk, actor=actor, expected_revision=revision(project))
    assert resolve(resolver_inputs, person=2).status == "MAPPING_MISSING"
    mapping = ensemble_services.save_mapping(
        project.pk,
        role_id=role.pk,
        instrument_id=parts[2].instrument_id,
        part_id=parts[1].pk,
        actor=actor,
        expected_revision=revision(project),
    )
    result = resolve(resolver_inputs, person=2)
    assert (
        result.part_origin == "ENSEMBLE_PROJECT"
        and result.mapping_id == mapping.pk
        and result.desired_part_id == parts[1].pk
    )
    sole = make(3, part=parts[0])
    exception = ensemble_services.save_mapping(
        project.pk,
        role_id=role.pk,
        instrument_id=parts[2].instrument_id,
        part_id=parts[0].pk,
        position_id=positions[0].pk,
        actor=actor,
        expected_revision=revision(project),
    )
    result = resolve(resolver_inputs, person=2)
    assert result.part_origin == "ENSEMBLE_POSITION" and result.assignment_id == sole.assignments.get().pk
    m.PartOverride.objects.create(
        project=project,
        position=positions[0],
        participant=people[2],
        desired_part=parts[1],
        edition=first.assignments.get(),
    )
    assert resolve(resolver_inputs, person=2).part_origin == "PERSONAL"
    assert exception.pk != mapping.pk


def test_revalidation_foreign_selection_and_inactive_catalog_block(resolver_inputs):
    actor, project, arr, parts, people, positions, first, _second, _make = resolver_inputs
    override = m.PartOverride.objects.create(
        project=project,
        position=positions[0],
        participant=people[1],
        desired_part=parts[1],
        edition=first.assignments.get(),
    )
    m.PartOverride.objects.filter(pk=override.pk).update(needs_revalidation=True)
    assert resolve(resolver_inputs).status == "INVALID"
    with pytest.raises(ValidationError):
        r.resolve_cell(project.pk, uuid.uuid4(), people[1].pk)
    with pytest.raises(ValidationError):
        r.resolve_cell(project.pk, positions[0].pk, uuid.uuid4())
    Part.objects.filter(pk=parts[2].pk).update(active=False)
    assert resolve(resolver_inputs, person=2).reasons == ("INACTIVE_DESIRED_PART",)


def test_corrupt_selected_copy_blocks_no_fallback_and_snapshot_pins_result(resolver_inputs, settings):
    actor, project, arr, parts, people, positions, first, second, _make = resolver_inputs
    m.PartOverride.objects.create(
        project=project,
        position=positions[0],
        participant=people[1],
        desired_part=parts[1],
        edition=first.assignments.get(),
    )
    result = resolve(resolver_inputs)
    (settings.CURATED_DIR / first.relative_path).write_bytes(b"synthetic corrupt bytes")
    corrupt = resolve(resolver_inputs)
    assert corrupt.status == "CORRUPT" and corrupt.assignment_id is None and corrupt.rule_id is None
    assert result.assignment_id == first.assignments.get().pk and result.sha256 == first.sha256
    assert corrupt.file_id == first.pk and corrupt.file_id != second.pk


def test_pure_resolution_has_no_queries_and_verification_once_per_file(
    resolver_inputs, django_assert_num_queries, monkeypatch
):
    _actor, project, _arr, parts, people, positions, first, _second, _make = resolver_inputs
    for position in positions[:2]:
        m.PartOverride.objects.create(
            project=project,
            position=position,
            participant=people[1],
            desired_part=parts[1],
            edition=first.assignments.get(),
        )
    session = r.ResolutionSession(project.pk)
    with django_assert_num_queries(0):
        assert session.resolve(positions[0].pk, people[1].pk).usable
        assert session.resolve(positions[1].pk, people[1].pk).usable
    calls = []
    original = r.library_services.verify_file

    def verify(file):
        calls.append(file.pk)
        return original(file)

    monkeypatch.setattr(r.library_services, "verify_file", verify)
    session.verified_resolution(positions[0].pk, people[1].pk)
    session.verified_resolution(positions[1].pk, people[1].pk)
    assert calls == [first.pk]


def test_same_musical_role_resolves_distinct_notation_variants(resolver_inputs):
    actor, project, arr, parts, people, positions, first, _second, make = resolver_inputs
    foreign = m.ProjectParticipant.objects.create(
        project=project, guest_id=uuid.uuid4(), display_name="Synthetic other notation", default_part=parts[3]
    )
    other_file = make(3, part=parts[3])
    role = ensemble_services.save_role(
        project.pk, code="3", label="Same musical role", actor=actor, expected_revision=1
    )
    for person in (people[2], foreign):
        ensemble_services.assign_role(project.pk, person.pk, role.pk, actor=actor, expected_revision=revision(project))
    for part in (parts[1], parts[3]):
        ensemble_services.save_mapping(
            project.pk,
            role_id=role.pk,
            instrument_id=part.instrument_id,
            part_id=part.pk,
            actor=actor,
            expected_revision=revision(project),
        )
    edition_services.set_preference(
        arr.pk, parts[1].pk, first.assignments.get().pk, actor=actor, expected_revision=arr.revision
    )
    session = r.ResolutionSession(project.pk)
    left = session.verified_resolution(positions[0].pk, people[2].pk)
    right = session.verified_resolution(positions[0].pk, foreign.pk)
    assert left.effective_part_id == parts[1].pk and right.effective_part_id == parts[3].pk
    assert right.file_id == other_file.pk and left.file_id == first.pk


def test_position_preference_revalidation_and_cyclic_tampered_rule_block(resolver_inputs):
    actor, project, arr, parts, people, positions, first, _second, _make = resolver_inputs
    preference = rule_services.set_edition(
        project.pk,
        arrangement_id=arr.pk,
        part_id=parts[1].pk,
        edition_id=first.assignments.get().pk,
        position_id=positions[0].pk,
        actor=actor,
        expected_revision=1,
    )
    m.PositionEditionPreference.objects.filter(pk=preference.pk).update(needs_revalidation=True)
    assert resolve(resolver_inputs).reasons == ("EDITION_REVALIDATION_REQUIRED",)
    m.ReplacementRule.objects.bulk_create(
        [
            m.ReplacementRule(project=project, desired_part=parts[2], replacement_part=parts[0]),
            m.ReplacementRule(project=project, desired_part=parts[0], replacement_part=parts[2]),
        ]
    )
    assert resolve(resolver_inputs, person=2).reasons == ("CYCLIC_REPLACEMENT_RULE",)


def test_source_missing_reuses_confirmed_copy_and_frozen_result(resolver_inputs):
    actor, project, arr, parts, _people, _positions, first, _second, _make = resolver_inputs
    edition_services.set_preference(
        arr.pk, parts[1].pk, first.assignments.get().pk, actor=actor, expected_revision=arr.revision
    )
    source = first.source_version.source_file
    review.mark_source_missing(source.pk, expected_revision=source.revision)
    result = resolve(resolver_inputs)
    assert result.usable and "SOURCE_MISSING_RETAINED_COPY" in result.warnings
    from dataclasses import FrozenInstanceError

    with pytest.raises(FrozenInstanceError):
        result.status = "MISSING"


def test_personal_incompatible_explicit_version_cannot_override_part(resolver_inputs):
    _actor, project, _arr, parts, people, positions, first, _second, _make = resolver_inputs
    m.PartOverride.objects.bulk_create(
        [
            m.PartOverride(
                project=project,
                position=positions[0],
                participant=people[2],
                desired_part=parts[2],
                edition=first.assignments.get(),
            )
        ]
    )
    result = resolve(resolver_inputs, person=2)
    assert result.status == "INVALID" and result.edition_origin == "PERSONAL" and result.assignment_id is None


def test_reserve_never_invokes_part_mapping_or_edition_selection(resolver_inputs, monkeypatch):
    _actor, project, _arr, _parts, people, positions, *_ = resolver_inputs
    session = r.ResolutionSession(project.pk)

    def denied(*args, **kwargs):
        pytest.fail("Reserve must not resolve musical assignment")

    monkeypatch.setattr(session, "_edition", denied)
    monkeypatch.setattr(r.ensemble_services, "mapping_choice", denied)
    assert session.verified_resolution(positions[2].pk, people[1].pk).status == "RESERVE"


def test_archive_withdrawal_during_hash_verification_is_not_usable(resolver_inputs, monkeypatch):
    actor, project, _arr, parts, people, positions, first, *_ = resolver_inputs
    m.PartOverride.objects.create(
        project=project,
        position=positions[0],
        participant=people[1],
        desired_part=parts[1],
        edition=first.assignments.get(),
    )
    original = r.library_services.verify_file

    def changed(file):
        valid = original(file)
        review.withdraw(file.pk, actor=actor, expected_revision=file.revision)
        return valid

    monkeypatch.setattr(r.library_services, "verify_file", changed)
    result = resolve(resolver_inputs)
    assert not result.usable and result.reasons == ("ARCHIVE_SELECTION_CHANGED",)


def test_position_replacement_priority_and_pending_music_not_selected(resolver_inputs):
    actor, project, arr, parts, people, positions, first, _second, make = resolver_inputs
    edition_services.set_preference(
        arr.pk, parts[1].pk, first.assignments.get().pk, actor=actor, expected_revision=arr.revision
    )
    rule_services.save_replacement(
        project_id=project.pk,
        desired_part_id=parts[2].pk,
        replacement_part_id=parts[0].pk,
        actor=actor,
        expected_revision=revision(project),
    )
    position_rule = rule_services.save_replacement(
        project_id=project.pk,
        position_id=positions[0].pk,
        desired_part_id=parts[2].pk,
        replacement_part_id=parts[1].pk,
        actor=actor,
        expected_revision=revision(project),
    )
    pending = make(3, part=parts[0], confirmed=False)
    result = resolve(resolver_inputs, person=2)
    assert result.status == "SUBSTITUTED" and result.replacement_origin == "POSITION"
    assert result.rule_id == position_rule.pk and result.assignment_id == first.assignments.get().pk
    elsewhere = resolve(resolver_inputs, person=2, position=1)
    assert elsewhere.status == "MISSING" and elsewhere.assignment_id is None
    assert pending.review_state == "PENDING"


def test_request_snapshot_keeps_prior_selection_after_project_edit(resolver_inputs):
    _actor, project, _arr, parts, people, positions, first, *_ = resolver_inputs
    override = m.PartOverride.objects.create(
        project=project,
        position=positions[0],
        participant=people[1],
        desired_part=parts[1],
        edition=first.assignments.get(),
    )
    session = r.ResolutionSession(project.pk)
    captured = session.resolve(positions[0].pk, people[1].pk)
    m.PartOverride.objects.filter(pk=override.pk).update(needs_revalidation=True)
    assert session.resolve(positions[0].pk, people[1].pk) == captured
    assert resolve(resolver_inputs).status == "INVALID"


def test_saved_member_default_does_not_follow_live_master_part(resolver_inputs):
    _actor, project, _arr, parts, people, positions, first, *_ = resolver_inputs
    from apps.members.models import Member

    member = Member.objects.create(name="Synthetic master", regular_part=parts[1])
    participant = m.ProjectParticipant.objects.create(
        project=project, member=member, display_name=member.name, default_part=parts[1]
    )
    member.regular_part = parts[0]
    member.save()
    session = r.ResolutionSession(project.pk)
    result = session.resolve(positions[0].pk, participant.pk)
    assert result.desired_part_id == parts[1].pk and result.part_origin == "SAVED_DEFAULT"


def test_confirmed_derivative_exact_choice_is_not_replaced_by_base(resolver_inputs):
    actor, project, arr, parts, people, positions, first, _second, make = resolver_inputs
    derivative = make(3, derivative=True)
    m.PartOverride.objects.create(
        project=project,
        position=positions[0],
        participant=people[1],
        desired_part=parts[1],
        edition=derivative.assignments.get(),
    )
    result = resolve(resolver_inputs)
    assert result.usable and result.file_id == derivative.pk and result.root_kind == "PROCESSED"
    assert result.file_id != first.pk and result.byte_size == derivative.byte_size
    assert result.edition_origin == "PERSONAL"
