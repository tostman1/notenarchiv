"""Preferred editions preserve exact compatible identities and review history."""

import hashlib

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import Client
from django.urls import reverse

from apps.archive import edition_services as e
from apps.archive import models as m
from apps.archive import services as s
from apps.catalog import models as c
from tests.archive_fixtures import PAGE
from tests.pdf_fixtures import pdf
from tests.test_archive_workflow import confirm, draft, receipt


@pytest.fixture
def edition_inputs(db, settings, tmp_path):
    actor = get_user_model().objects.create_user("synthetic-editions")
    arrangement = c.Arrangement.objects.create(work=c.Work.objects.create(title="Synthetic editions"))
    variants = [
        c.InstrumentVariant.objects.create(name="Posaune", transposition=key, clef=clef)
        for key, clef in [("C", "BASS"), ("B", "TREBLE")]
    ]
    parts = [c.Part.objects.create(instrument=variant, code="2") for variant in variants]
    settings.CURATED_DIR = tmp_path / "clean"
    settings.PROCESSED_DIR = tmp_path / "processed"
    folder = m.SourceFolder.objects.create(relative_path="Synthetic editions")

    def make(number, *, part=parts[0], owner=arrangement, confirmed=True, derivative=False):
        data = pdf(text=bool(number % 2))
        version, _ = s.observe_version(
            folder.pk,
            f"Synthetic editions/{number}.pdf",
            sha256=hashlib.sha256(data).hexdigest(),
            byte_size=len(data),
            pdf_state="VALID",
            page_info=[PAGE],
        )
        file = s.register_base(version.pk, f"_Ungeprueft/{number}.pdf")
        if derivative:
            file = m.ArchiveFile.objects.create(
                source_version=version,
                relative_path=f"_Ungeprueft/derived-{number}.pdf",
                root_kind="PROCESSED",
                kind="DERIVATIVE",
                derived_from=file,
                sha256=hashlib.sha256(data).hexdigest(),
                byte_size=len(data),
                processing_profile="synthetic",
                processing_version="1",
            )
        file, _ = receipt(file, kind="DERIVATIVE" if derivative else "COPY")
        if confirmed:
            file = confirm(file, draft(file, actor, owner, [part]), actor, path=f"Synthetic editions/{number}.pdf")
        root = settings.PROCESSED_DIR if derivative else settings.CURATED_DIR
        path = root / file.relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return file

    first, second = make(1), make(2)
    return actor, arrangement, parts, first, second, make


def revision(arrangement):
    arrangement.refresh_from_db()
    return arrangement.revision


def choose(inputs, file):
    actor, arrangement, parts, *_ = inputs
    return e.set_preference(
        arrangement.pk,
        parts[0].pk,
        file.assignments.get().pk if file else None,
        actor=actor,
        expected_revision=revision(arrangement),
    )


def test_multiple_editions_preference_reset_and_explicit_choice_are_distinct(edition_inputs):
    _actor, arrangement, parts, first, second, _make = edition_inputs
    assert e.resolve(arrangement.pk, parts[0].pk).status == "AMBIGUOUS"
    first_id, second_id = first.assignments.get().pk, second.assignments.get().pk
    preference = choose(edition_inputs, first)
    assert e.resolve(arrangement.pk, parts[0].pk).assignment.pk == first_id
    choose(edition_inputs, second)
    result = e.resolve(arrangement.pk, parts[0].pk, explicit_assignment_id=first_id)
    assert (result.origin, result.assignment.pk) == ("EXPLICIT", first_id)
    assert e.resolve(arrangement.pk, parts[0].pk).assignment.pk == second_id
    cleared = choose(edition_inputs, None)
    assert cleared.pk == preference.pk and cleared.assignment_id is None
    assert e.resolve(arrangement.pk, parts[0].pk).status == "AMBIGUOUS"
    assert preference.changes.count() == 3 and m.ArchiveFile.objects.usable().count() == 2


def test_transposition_clef_part_and_arrangement_must_match(edition_inputs):
    actor, arrangement, parts, first, _second, make = edition_inputs
    foreign = c.Arrangement.objects.create(work=arrangement.work, edition="Incompatible arrangement")
    for file in (make(3, part=parts[1]), make(4, owner=foreign), make(5, confirmed=False)):
        selected = file.assignments.first()
        with pytest.raises(ValidationError):
            e.set_preference(
                arrangement.pk,
                parts[0].pk,
                selected.pk if selected else file.pk,
                actor=actor,
                expected_revision=revision(arrangement),
            )
        assert not m.PreferredEdition.objects.exists()
    assert (
        e.resolve(arrangement.pk, parts[1].pk, explicit_assignment_id=first.assignments.get().pk).status
        == "UNAVAILABLE"
    )
    assert e.resolve(arrangement.pk, parts[0].pk, explicit_assignment_id="not-a-uuid").status == "UNAVAILABLE"


@pytest.mark.parametrize("change", ["withdrawn", "missing", "corrupt", "inactive"])
def test_invalid_preference_or_explicit_choice_never_substituted(edition_inputs, settings, change):
    actor, arrangement, parts, first, second, _make = edition_inputs
    preferred = choose(edition_inputs, first)
    if change == "withdrawn":
        s.withdraw(first.pk, actor=actor, expected_revision=first.revision)
    elif change == "missing":
        m.ArchiveFile.objects.filter(pk=first.pk).update(publication_state="MISSING")
    elif change == "inactive":
        c.Part.objects.filter(pk=parts[0].pk).update(active=False)
    else:
        (settings.CURATED_DIR / first.relative_path).write_bytes(b"corrupt synthetic")
    assert e.resolve(arrangement.pk, parts[0].pk).status == "UNAVAILABLE"
    assert (
        e.resolve(arrangement.pk, parts[0].pk, explicit_assignment_id=preferred.assignment_id).status == "UNAVAILABLE"
    )
    assert m.PreferredEdition.objects.get(pk=preferred.pk).assignment_id == preferred.assignment_id
    assert m.ArchiveFile.objects.filter(pk=second.pk).exists()


def test_sole_edition_missing_and_independently_approved_derivative(edition_inputs):
    _actor, arrangement, parts, _first, _second, make = edition_inputs
    assert e.resolve(arrangement.pk, parts[1].pk).status == "MISSING"
    sole = make(3, part=parts[1])
    result = e.resolve(arrangement.pk, parts[1].pk)
    assert result.origin == "SOLE" and result.assignment.archive_file_id == sole.pk
    derivative = make(4, derivative=True)
    choose(edition_inputs, derivative)
    assert e.resolve(arrangement.pk, parts[0].pk).assignment.archive_file.kind == "DERIVATIVE"


def test_stale_write_uniqueness_and_protected_history(edition_inputs):
    actor, arrangement, parts, first, second, _make = edition_inputs
    original = revision(arrangement)
    preferred = choose(edition_inputs, first)
    with pytest.raises(s.ArchiveConflict):
        e.set_preference(
            arrangement.pk, parts[0].pk, second.assignments.get().pk, actor=actor, expected_revision=original
        )
    with pytest.raises(IntegrityError), transaction.atomic():
        m.PreferredEdition.objects.bulk_create([m.PreferredEdition(arrangement=arrangement, part=parts[0])])
    choose(edition_inputs, second)
    with pytest.raises(ProtectedError):
        m.ArchiveAssignment.objects.filter(pk=first.assignments.get().pk).delete()
    with pytest.raises(ValidationError):
        preferred.changes.first().save()
    assert preferred.changes.count() == 2


def test_preferences_auth_csrf_get_is_readonly_and_conflicts(edition_inputs, client):
    actor, arrangement, parts, first, _second, _make = edition_inputs
    url = reverse("archive_editions", args=[arrangement.pk, parts[0].pk])
    assert client.get(url).status_code == 302
    client.force_login(actor)
    assert client.get(url).status_code == 200 and not m.PreferredEdition.objects.exists()
    data = {"assignment": str(first.assignments.get().pk), "expected_revision": revision(arrangement)}
    csrf = Client(enforce_csrf_checks=True)
    csrf.force_login(actor)
    assert csrf.post(url, data).status_code == 403
    assert client.post(url, data).status_code == 302
    assert client.post(url, data).status_code == 409
    assert client.get(url, {"selection": "bad"}).status_code == 200
    assert client.post(url, {"assignment": "bad", "expected_revision": revision(arrangement)}).status_code == 400


def test_inactive_preference_can_be_explicitly_cleared(edition_inputs):
    _actor, arrangement, parts, first, _second, _make = edition_inputs
    preference = choose(edition_inputs, first)
    c.Part.objects.filter(pk=parts[0].pk).update(active=False)
    assert e.resolve(arrangement.pk, parts[0].pk).status == "UNAVAILABLE"
    cleared = choose(edition_inputs, None)
    assert cleared.pk == preference.pk and cleared.assignment_id is None
    assert e.resolve(arrangement.pk, parts[0].pk).status == "MISSING"


def test_hash_check_race_and_inactive_actor_roll_back_revision(edition_inputs, monkeypatch):
    actor, arrangement, parts, first, _second, _make = edition_inputs
    assignment = first.assignments.get()
    old = revision(arrangement)
    original = e.library_services.verify_file

    def changed(file):
        verified = original(file)
        s.withdraw(file.pk, actor=actor, expected_revision=file.revision)
        return verified

    monkeypatch.setattr(e.library_services, "verify_file", changed)
    with pytest.raises(s.ArchiveConflict):
        e.set_preference(arrangement.pk, parts[0].pk, assignment.pk, actor=actor, expected_revision=old)
    assert revision(arrangement) == old and not m.PreferredEdition.objects.exists()
    monkeypatch.setattr(e.library_services, "verify_file", original)
    actor.is_active = False
    actor.save()
    with pytest.raises(ValidationError):
        e.set_preference(arrangement.pk, parts[0].pk, None, actor=actor, expected_revision=old)
    assert revision(arrangement) == old


def test_preference_model_rejects_cross_scope_and_keeps_combined_parts_independent(edition_inputs):
    actor, arrangement, parts, first, _second, make = edition_inputs
    foreign = make(3, part=parts[1])
    with pytest.raises(ValidationError):
        m.PreferredEdition.objects.create(arrangement=arrangement, part=parts[0], assignment=foreign.assignments.get())
    other = c.Part.objects.create(instrument=parts[0].instrument, code="3")
    # A fresh inspected approval explicitly confirms both combined assignments.
    first = confirm(
        first, draft(first, actor, arrangement, [parts[0], other]), actor, path="Synthetic editions/combined.pdf"
    )
    from pathlib import Path

    from django.conf import settings

    path = Path(settings.CURATED_DIR) / first.relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(pdf(text=True))
    for part in (parts[0], other):
        e.set_preference(
            arrangement.pk,
            part.pk,
            first.assignments.get(part=part).pk,
            actor=actor,
            expected_revision=revision(arrangement),
        )
    assert m.PreferredEdition.objects.count() == 2
    assert e.resolve(arrangement.pk, other.pk).assignment.archive_file_id == first.pk


def test_withdrawn_without_preference_remains_visible_but_not_selectable(edition_inputs, client):
    actor, arrangement, parts, _first, _second, make = edition_inputs
    only = make(3, part=parts[1])
    s.withdraw(only.pk, actor=actor, expected_revision=only.revision)
    client.force_login(actor)
    response = client.get(reverse("archive_library_arrangement", args=[arrangement.pk]))
    assert response.status_code == 200
    assert "zurückgezogene Versionen" in response.content.decode()
    response = client.get(reverse("archive_editions", args=[arrangement.pk, parts[1].pk]))
    assert response.context["resolution"].status == "MISSING"
    assert not response.context["page"][0].available
