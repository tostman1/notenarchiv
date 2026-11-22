"""Title/alias substrings, independent expectation/material and usable versions."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.archive import library_services as service
from apps.archive import models as m
from apps.archive import services as s
from apps.catalog import models as c
from tests.test_archive_workflow import confirm, draft, receipt


@pytest.fixture
def library_inputs(archive, client, settings, tmp_path):
    _folder, _version, file, data = archive
    actor = get_user_model().objects.create_user("synthetic-library")
    client.force_login(actor)
    works = [
        c.Work.objects.create(title=title) for title in ("ABBA Medley", "Abel Tasman", "Fuchsgraben Polka", "Other")
    ]
    arrangements = [c.Arrangement.objects.create(work=work) for work in works]
    c.WorkAlias.objects.create(work=works[-1], alias="Synthetischer Ab-Titel")
    variant = c.InstrumentVariant.objects.create(name="Posaune", transposition="C", clef="BASS")
    parts = [c.Part.objects.create(instrument=variant, code=str(n)) for n in (1, 2, 3, 4)]
    file, _ = receipt(file)
    file = confirm(file, draft(file, actor, arrangements[0], parts[:1]), actor)
    settings.CURATED_DIR = tmp_path / "clean"
    path = settings.CURATED_DIR / file.relative_path
    path.parent.mkdir(parents=True)
    path.write_bytes(data)
    return client, file, actor, arrangements, variant, parts, path


def test_substring_alias_and_unicode_search_find_prefix_and_interior(library_inputs):
    client, _file, _actor, arrangements, *_ = library_inputs
    ids = set(service.search({"q": "ａｂ"}).values_list("pk", flat=True))
    assert ids == {item.pk for item in arrangements}
    assert service.search({"q": "graben"}).get().pk == arrangements[2].pk
    response = client.get(reverse("archive_library"), {"q": "AB"})
    assert response.status_code == 200 and response.context["page"].paginator.count == 4


def test_expectations_remain_unknown_despite_confirmation_and_optional_is_separate(library_inputs):
    _client, _file, _actor, arrangements, _variant, parts, _path = library_inputs
    arrangement = service.search({}).get(pk=arrangements[0].pk)
    assert service.completeness(arrangement) == "UNKNOWN"
    rows = service.part_rows(arrangement)
    assert rows[0]["state"] == "AVAILABLE" and rows[0]["expectation"] == "UNKNOWN"
    c.Arrangement.objects.filter(pk=arrangement.pk).update(expectations_defined=True)
    c.ExpectedPart.objects.create(arrangement=arrangement, part=parts[0], required=True)
    c.ExpectedPart.objects.create(arrangement=arrangement, part=parts[1], required=True)
    c.ExpectedPart.objects.create(arrangement=arrangement, part=parts[2], required=False)
    arrangement = service.search({}).get(pk=arrangement.pk)
    assert service.completeness(arrangement) == "INCOMPLETE"
    rows = {row["part"].pk: row for row in service.part_rows(arrangement)}
    assert rows[parts[1].pk]["state"] == "MISSING"
    assert rows[parts[2].pk]["expectation"] == "NOT_REQUIRED" and rows[parts[2].pk]["optional"]
    assert service.search({"completeness": "INCOMPLETE"}).get().pk == arrangement.pk
    assert service.search({"review": "CONFIRMED"}).get().pk == arrangement.pk


def test_current_unreviewed_proposals_are_not_available(library_inputs):
    client, file, actor, arrangements, _variant, parts, _path = library_inputs
    # A correction to a confirmed file must not revoke or relabel its prior assignment.
    proposal = s.create_proposal(
        file.pk, actor=actor, arrangement_id=arrangements[1].pk, part_ids=[parts[1].pk], expected_revision=file.revision
    )
    assert proposal.state == "DRAFT" and service.search({"review": "CONFIRMED"}).get().pk == arrangements[0].pk
    response = client.get(reverse("archive_library_arrangement", args=[arrangements[0].pk]))
    assert response.status_code == 200 and len(response.context["editions"]) == 1
    assert response.context["editions"][0].physically_verified


def test_invalid_filters_auth_and_corrupt_copy_do_not_present_music_as_usable(library_inputs):
    client, file, _actor, arrangements, _variant, parts, path = library_inputs
    assert client.get(reverse("archive_library"), {"review": "injected"}).status_code == 400
    assert client.get(reverse("archive_library"), {"part": "../escape"}).status_code == 400
    other = c.InstrumentVariant.objects.create(name="Other variant")
    assert (
        client.get(reverse("archive_library"), {"instrument": str(other.pk), "part": str(parts[0].pk)}).status_code
        == 400
    )
    path.write_bytes(b"Synthetic corrupted CLEAN")
    response = client.get(reverse("archive_library_arrangement", args=[arrangements[0].pk]))
    assert not response.context["editions"][0].physically_verified
    assert "nicht nutzbar" in response.content.decode()
    assert not service.verify_file(file)
    client.logout()
    assert client.get(reverse("archive_library")).status_code == 302


def test_defined_empty_and_complete_filter_are_not_unknown(library_inputs):
    _client, _file, _actor, arrangements, _variant, parts, _path = library_inputs
    c.Arrangement.objects.filter(pk__in=[arrangements[0].pk, arrangements[1].pk]).update(expectations_defined=True)
    c.ExpectedPart.objects.create(arrangement=arrangements[0], part=parts[0], required=True)
    assert service.search({"completeness": "COMPLETE"}).get().pk == arrangements[0].pk
    assert service.search({"completeness": "NOT_REQUIRED"}).get().pk == arrangements[1].pk
    assert service.search({"instrument": parts[0].instrument}).get().pk == arrangements[0].pk


def test_pending_candidate_and_manual_correction_show_unreviewed_not_available(library_inputs):
    import hashlib

    from apps.archive.recognition import record_candidate
    from tests.archive_fixtures import PAGE

    client, file, actor, arrangements, variant, parts, path = library_inputs
    folder = file.source_version.source_file.folder
    data = path.read_bytes()
    version, _ = s.observe_version(
        folder.pk,
        "Synthetic/unknown.pdf",
        sha256=hashlib.sha256(data).hexdigest(),
        byte_size=len(data),
        pdf_state="VALID",
        page_info=[PAGE],
    )
    pending = s.register_base(version.pk, "_Ungeprueft/unknown.pdf")
    pending, _ = receipt(pending)
    record_candidate(version.pk, filename="Abel Tasman Posaune 2.pdf", text_lines=["Abel Tasman", "Posaune 2"])
    arrangement = service.search({}).get(pk=arrangements[1].pk)
    rows = service.part_rows(arrangement)
    assert rows and rows[0]["state"] == "UNREVIEWED"
    assert service.search({"review": "PENDING", "part": parts[1]}).get().pk == arrangement.pk
    s.create_proposal(
        pending.pk,
        actor=actor,
        arrangement_id=arrangements[2].pk,
        part_ids=[parts[2].pk],
        expected_revision=pending.revision,
    )
    assert not service.part_rows(arrangement)
    corrected = service.search({}).get(pk=arrangements[2].pk)
    assert service.part_rows(corrected)[0]["state"] == "UNREVIEWED"
    response = client.get(reverse("archive_library_arrangement", args=[corrected.pk]))
    assert "Ungeprüft" in response.content.decode() and response.context["editions"].paginator.count == 0


def test_inactive_and_missing_or_withdrawn_versions_do_not_count_available(library_inputs):
    _client, file, actor, arrangements, _variant, parts, _path = library_inputs
    arrangement = arrangements[0]
    c.Arrangement.objects.filter(pk=arrangement.pk).update(expectations_defined=True)
    c.ExpectedPart.objects.create(arrangement=arrangement, part=parts[0], required=True)
    m.ArchiveFile.objects.filter(pk=file.pk).update(publication_state="MISSING")
    assert service.search({"completeness": "INCOMPLETE"}).get().pk == arrangement.pk
    assert not service.search({"review": "CONFIRMED"}).exists()
    m.ArchiveFile.objects.filter(pk=file.pk).update(publication_state="AVAILABLE")
    s.withdraw(file.pk, actor=actor, expected_revision=file.revision)
    assert not service.search({"review": "CONFIRMED"}).exists()
    assert service.part_rows(service.search({}).get(pk=arrangement.pk))[0]["state"] == "MISSING"


def test_duplicate_titles_and_bounded_pages_remain_separate(library_inputs):
    client, _file, _actor, arrangements, *_ = library_inputs
    for _number in range(26):
        work = c.Work.objects.create(title="ABBA Medley")
        c.Arrangement.objects.create(work=work, edition="Synthetic other edition")
    response = client.get(reverse("archive_library"), {"q": "abba"})
    assert len(response.context["page"]) == 25 and response.context["page"].paginator.count == 27
    assert arrangements[0].pk in set(service.search({"q": "abba"}).values_list("pk", flat=True))
