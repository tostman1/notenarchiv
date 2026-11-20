"""Catalog identity, canonical constraints, expectation copy and reference safety."""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.catalog import forms, models, services
from apps.members.forms import MemberForm
from apps.members.models import Member


def create(model, **values):
    return services.save_record(model(**values))


@pytest.fixture
def catalog(db):
    work = create(models.Work, title="Synthetischer Marsch")
    arrangement = create(models.Arrangement, work=work, arranger="Synthetische Bearbeitung")
    instrument = create(models.InstrumentVariant, name="Synthetische Klarinette", transposition="B")
    part = create(models.Part, instrument=instrument, code="1")
    return work, arrangement, instrument, part


def test_equal_titles_and_human_names_remain_distinct(catalog):
    work, arrangement, _instrument, part = catalog
    other = create(models.Work, title=work.title)
    second_arrangement = create(models.Arrangement, work=work, arranger=arrangement.arranger)
    first = create(Member, name="Synthetischer Gleichname", regular_part=part)
    second = create(Member, name=first.name, regular_part=part)
    assert work.pk != other.pk and arrangement.pk != second_arrangement.pk and first.pk != second.pk
    assert str(work) != str(other) and str(first) != str(second)


def test_variants_and_parts_have_normalized_non_null_identity(catalog):
    _work, _arrangement, instrument, part = catalog
    bass = create(models.InstrumentVariant, name=instrument.name, transposition="B", clef="BASS")
    c_variant = create(models.InstrumentVariant, name=instrument.name, transposition="C")
    assert len({instrument.pk, bass.pk, c_variant.pk}) == 3
    with pytest.raises(ValidationError):
        create(models.InstrumentVariant, name="  SYNTHETISCHE KLARINETTE ", transposition="b")
    with pytest.raises(IntegrityError), transaction.atomic():
        models.InstrumentVariant.objects.create(name=instrument.name, transposition="B")
    with pytest.raises(ValidationError):
        create(models.Part, instrument=instrument, code=" 1 ")
    assert create(models.Part, instrument=bass, code=part.code).pk != part.pk
    with pytest.raises(ValidationError):
        create(models.InstrumentVariant, name="", transposition="C")


def test_aliases_are_explicit_and_ambiguity_does_not_merge_targets(catalog):
    work, _arrangement, instrument, part = catalog
    create(models.WorkAlias, work=work, alias="Marschstraße")
    with pytest.raises(ValidationError):
        create(models.WorkAlias, work=work, alias=" MARSCHSTRASSE ")
    other_work = create(models.Work, title=work.title)
    create(models.WorkAlias, work=other_work, alias="Marschstraße")
    create(models.InstrumentAlias, alias="Stimme I", instrument=instrument)
    create(models.InstrumentAlias, alias="Stimme I", part=part)
    for values in ({}, {"instrument": instrument, "part": part}):
        with pytest.raises(ValidationError):
            create(models.InstrumentAlias, alias="invalid", **values)
    with pytest.raises(IntegrityError), transaction.atomic():
        models.InstrumentAlias.objects.create(alias="bad", instrument=instrument, part=part)
    assert models.Work.objects.count() == 2 and models.InstrumentAlias.objects.count() == 2


def test_member_assignment_is_required_and_never_free_text(catalog):
    _work, _arrangement, _instrument, part = catalog
    with pytest.raises(ValidationError):
        create(Member, name="Synthetic missing part")
    with pytest.raises(IntegrityError), transaction.atomic():
        Member.objects.create(name="Synthetic missing part")
    form = MemberForm({"name": "Synthetic", "regular_part": "Klarinette 1", "active": True, "expected_revision": 0})
    assert not form.is_valid() and "regular_part" in form.errors
    valid = MemberForm({"name": "Synthetic", "regular_part": str(part.pk), "active": True, "expected_revision": 0})
    assert valid.is_valid(), valid.errors
    member = services.save_record(valid.save(commit=False))
    assert member.regular_part == part
    assert valid.fields["regular_part"].label == "Stammstimme"


def test_used_parts_cannot_be_deleted_or_deactivated_under_active_members(catalog):
    work, _arrangement, instrument, part = catalog
    member = create(Member, name="Synthetic", regular_part=part)
    for record in (work, part, instrument):
        with pytest.raises(ValidationError, match="verwendet"):
            services.delete_record(record, expected_revision=record.revision)
    for record in (part, instrument):
        record.refresh_from_db()
        record.active = False
        with pytest.raises(ValidationError, match="Aktive Mitglieder"):
            services.save_record(record, expected_revision=record.revision)
        record.refresh_from_db()
        assert record.active
    member.active = False
    services.save_record(member, expected_revision=member.revision)
    part.active = False
    services.save_record(part, expected_revision=part.revision)
    member.active = True
    with pytest.raises(ValidationError):
        services.save_record(member, expected_revision=member.revision)
    assert Member.objects.get(pk=member.pk).regular_part_id == part.pk


def test_unknown_empty_and_defined_expectations_are_distinct(catalog):
    _work, arrangement, _instrument, part = catalog
    assert not arrangement.expectations_defined and not arrangement.expected_parts.exists()
    entry = create(models.ExpectedPart, arrangement=arrangement, part=part, required=False)
    arrangement.refresh_from_db()
    assert arrangement.expectations_defined
    arrangement.expectations_defined = False
    with pytest.raises(ValidationError):
        services.save_record(arrangement, expected_revision=arrangement.revision)
    services.delete_record(entry, expected_revision=entry.revision)
    arrangement.refresh_from_db()
    assert arrangement.expectations_defined and not arrangement.expected_parts.exists()
    arrangement.expectations_defined = False
    services.save_record(arrangement, expected_revision=arrangement.revision)
    assert not models.Arrangement.objects.get(pk=arrangement.pk).expectations_defined


def test_templates_copy_required_and_optional_parts_without_live_mutation(catalog):
    _work, arrangement, instrument, part = catalog
    second = create(models.Part, instrument=instrument, code="2")
    template = create(models.InstrumentationTemplate, name="Synthetische Besetzung")
    first_entry = create(models.TemplatePart, template=template, part=part)
    create(models.TemplatePart, template=template, part=second, required=False)
    arrangement = services.apply_template(arrangement.pk, template, expected_revision=arrangement.revision)
    assert arrangement.expectations_defined
    assert dict(arrangement.expected_parts.values_list("part_id", "required")) == {part.pk: True, second.pk: False}
    first_entry.required = False
    services.save_record(first_entry, expected_revision=first_entry.revision)
    assert arrangement.expected_parts.get(part=part).required
    with pytest.raises(ValidationError, match="ausdrücklich"):
        services.apply_template(arrangement.pk, template, expected_revision=arrangement.revision)
    arrangement = services.apply_template(
        arrangement.pk, template, expected_revision=arrangement.revision, replace=True
    )
    assert not arrangement.expected_parts.get(part=part).required
    with pytest.raises(services.EditConflict):
        services.apply_template(arrangement.pk, template, expected_revision=arrangement.revision - 1, replace=True)


def test_invalid_template_leaves_existing_expectations_and_revision_intact(catalog):
    _work, arrangement, instrument, part = catalog
    existing = create(models.ExpectedPart, arrangement=arrangement, part=part)
    other = create(models.Part, instrument=instrument, code="2")
    template = create(models.InstrumentationTemplate, name="Synthetic")
    create(models.TemplatePart, template=template, part=other)
    other.active = False
    services.save_record(other, expected_revision=other.revision)
    arrangement.refresh_from_db()
    revision = arrangement.revision
    with pytest.raises(ValidationError, match="inaktive"):
        services.apply_template(arrangement.pk, template, expected_revision=revision, replace=True)
    arrangement.refresh_from_db()
    assert arrangement.revision == revision and list(arrangement.expected_parts.values_list("pk", flat=True)) == [
        existing.pk
    ]


def test_stale_edits_do_not_overwrite_and_unused_deletion_requires_revision(catalog):
    work, _arrangement, _instrument, _part = catalog
    first, second = models.Work.objects.get(pk=work.pk), models.Work.objects.get(pk=work.pk)
    first.composer = "Synthetic first"
    services.save_record(first, expected_revision=first.revision)
    second.composer = "Synthetic stale"
    with pytest.raises(services.EditConflict):
        services.save_record(second, expected_revision=second.revision)
    assert models.Work.objects.get(pk=work.pk).composer == "Synthetic first"
    spare = create(models.Work, title="Unreferenced synthetic work")
    spare_id = spare.pk
    with pytest.raises(services.EditConflict):
        services.delete_record(spare, expected_revision=0)
    services.delete_record(spare, expected_revision=spare.revision)
    assert not models.Work.objects.filter(pk=spare_id).exists()


def test_inactive_choices_cannot_be_assigned_as_new_references(catalog):
    _work, arrangement, instrument, part = catalog
    part.active = False
    services.save_record(part, expected_revision=part.revision)
    form = forms.ExpectedPartForm(
        {"arrangement": str(arrangement.pk), "part": str(part.pk), "required": True, "expected_revision": 0}
    )
    assert not form.is_valid() and "part" in form.errors
    with pytest.raises(ValidationError):
        create(models.ExpectedPart, arrangement=arrangement, part=part)
    instrument.active = False
    services.save_record(instrument, expected_revision=instrument.revision)
    assert not forms.PartForm().fields["instrument"].queryset.filter(pk=instrument.pk).exists()


@pytest.mark.parametrize("text", ["", " " * 4, "x" * 201])
def test_invalid_work_titles_are_rejected(db, text):
    with pytest.raises(ValidationError):
        create(models.Work, title=text)


def test_empty_template_is_an_explicit_known_empty_list(catalog):
    _work, arrangement, _instrument, _part = catalog
    template = create(models.InstrumentationTemplate, name="Synthetic empty list")
    services.apply_template(arrangement.pk, template, expected_revision=arrangement.revision)
    arrangement.refresh_from_db()
    assert arrangement.expectations_defined and not arrangement.expected_parts.exists()


def test_database_rejects_duplicate_expectations_and_template_entries(catalog):
    _work, arrangement, _instrument, part = catalog
    create(models.ExpectedPart, arrangement=arrangement, part=part)
    template = create(models.InstrumentationTemplate, name="Synthetic")
    create(models.TemplatePart, template=template, part=part)
    for model, values in (
        (models.ExpectedPart, {"arrangement": arrangement}),
        (models.TemplatePart, {"template": template}),
    ):
        with pytest.raises(IntegrityError), transaction.atomic():
            model.objects.create(part=part, **values)


def test_oversized_template_does_not_replace_target(catalog):
    _work, arrangement, instrument, part = catalog
    existing = create(models.ExpectedPart, arrangement=arrangement, part=part)
    template = create(models.InstrumentationTemplate, name="Synthetic bounded list")
    parts = [models.Part(instrument=instrument, code=str(index + 10)) for index in range(1001)]
    for entry in parts:
        entry.normalize()
    models.Part.objects.bulk_create(parts)
    models.TemplatePart.objects.bulk_create([models.TemplatePart(template=template, part=entry) for entry in parts])
    arrangement.refresh_from_db()
    before = arrangement.revision
    with pytest.raises(ValidationError, match="1000"):
        services.apply_template(arrangement.pk, template, expected_revision=before, replace=True)
    arrangement.refresh_from_db()
    assert arrangement.revision == before and arrangement.expected_parts.get().pk == existing.pk


@pytest.mark.parametrize("field,value", [("code", "2"), ("instrument", "other")])
def test_used_part_cannot_silently_change_musical_identity(catalog, field, value):
    _work, _arrangement, instrument, part = catalog
    member = create(Member, name="Synthetic protected member", regular_part=part)
    if field == "instrument":
        value = create(models.InstrumentVariant, name=instrument.name, transposition="C")
    setattr(part, field, value)
    with pytest.raises(ValidationError, match="musikalische Zuordnung"):
        services.save_record(part, expected_revision=part.revision)
    member.refresh_from_db()
    assert member.regular_part.code == "1" and member.regular_part.instrument_id == instrument.pk


@pytest.mark.parametrize(
    "field,value", [("transposition", "C"), ("clef", "BASS"), ("name", "Other instrument"), ("family", "Other family")]
)
def test_used_variant_cannot_reinterpret_existing_parts(catalog, field, value):
    _work, _arrangement, instrument, part = catalog
    setattr(instrument, field, value)
    with pytest.raises(ValidationError, match="musikalische Zuordnung"):
        services.save_record(instrument, expected_revision=instrument.revision)
    part.refresh_from_db()
    assert part.instrument.transposition == "B" and part.instrument.clef == "TREBLE"
    part.label = "Synthetic descriptive correction"
    services.save_record(part, expected_revision=part.revision)
    assert models.Part.objects.get(pk=part.pk).label == "Synthetic descriptive correction"
