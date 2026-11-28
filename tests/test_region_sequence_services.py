"""Explicit saved sequences remain proposals, with exact input/history pins."""

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import Client
from django.urls import reverse

from apps.archive import models as m
from apps.archive import region_sequence_services
from apps.archive.region_sequence_services import propose_region_sequence
from apps.archive.services import ArchiveConflict
from apps.catalog import models as c
from tests.test_region_preview import region_preview  # noqa: F401


def propose(file, regions, **overrides):
    arrangement = c.Arrangement.objects.create(work=c.Work.objects.create(title="Synthetic selected work"))
    part = c.Part.objects.create(instrument=c.InstrumentVariant.objects.create(name="Synthetic part"), code="1")
    edition = m.ContentEdition.objects.create(arrangement=arrangement, part=part)
    values = {
        "edition_id": edition.pk,
        "expected_edition_number": 0,
        "expected_file_revision": file.revision,
        "source_version_id": file.source_version_id,
        "region_revision_ids": [region.pk for region in regions],
    }
    values.update(overrides)
    return propose_region_sequence(file.pk, **values)


@pytest.mark.django_db
def test_explicit_sequence_preserves_repeated_occurrences_without_approval(region_preview):  # noqa: F811
    file, regions, target = region_preview
    original = target.read_bytes()
    revision = propose(file, [regions[1], regions[1]])
    references = list(revision.references.order_by("sequence"))
    assert len(references) == 2 and references[0].pk != references[1].pk
    assert references[0].logical_page_revision_id == references[1].logical_page_revision_id
    assert references[0].logical_page_revision.region_revision_id == regions[1].pk
    assert target.read_bytes() == original
    assert m.ContentInspection.objects.count() == m.ContentConfirmation.objects.count() == 0
    assert m.ReviewInspection.objects.count() == 0
    file.refresh_from_db()
    assert file.review_state == "PENDING" and file.current_proposal_id is None


@pytest.mark.django_db
@pytest.mark.parametrize("override", [{"expected_file_revision": 99}, {"expected_edition_number": 1}])
def test_stale_sequence_rolls_back_all_new_logical_rows(region_preview, override):  # noqa: F811
    file, regions, _ = region_preview
    with pytest.raises(ArchiveConflict):
        propose(file, [regions[1]], **override)
    assert m.LogicalPage.objects.count() == m.LogicalPageRevision.objects.count() == 0
    assert m.ContentEditionRevision.objects.count() == 0


@pytest.mark.django_db
def test_historical_region_can_be_previewed_but_not_silently_reused_in_new_proposal(region_preview):  # noqa: F811
    file, regions, _ = region_preview
    with pytest.raises(ArchiveConflict):
        propose(file, [regions[0]])
    assert m.ContentEditionRevision.objects.count() == m.LogicalPage.objects.count() == 0


@pytest.mark.django_db
@pytest.mark.parametrize("ids", [[], ["invalid"], ["0" * 32] * 17])
def test_explicit_sequence_requires_bounded_uuid_inputs(region_preview, ids):  # noqa: F811
    file, regions, _ = region_preview
    with pytest.raises(ValidationError):
        propose(file, [regions[1]], region_revision_ids=ids)
    assert m.LogicalPage.objects.count() == m.ContentEditionRevision.objects.count() == 0


@pytest.mark.django_db
@pytest.mark.parametrize("state", ["MISSING", "CORRUPT"])
def test_sequence_rechecks_health_after_verified_read(region_preview, monkeypatch, state):  # noqa: F811
    file, regions, _ = region_preview
    original = region_sequence_services.preview_bytes

    def changed_health(source):
        data = original(source)
        m.ArchiveFile.objects.filter(pk=source.pk).update(publication_state=state)
        return data

    monkeypatch.setattr(region_sequence_services, "preview_bytes", changed_health)
    with pytest.raises(ArchiveConflict):
        propose(file, [regions[1]])
    assert m.LogicalPage.objects.count() == m.ContentEditionRevision.objects.count() == 0


@pytest.mark.django_db
def test_sequence_order_and_later_proposals_retain_earlier_pins(region_preview):  # noqa: F811
    file, regions, _ = region_preview
    page = regions[1].region.source_page
    other = m.PageRegion.objects.create(source_page=page)
    other_revision = m.PageRegionRevision.objects.create(
        region=other, number=1, bounds_points=[0, 0, 50, 80], page_fingerprint=page.geometry_fingerprint
    )
    first = propose(file, [other_revision, regions[1], other_revision])
    first_ids = list(first.references.order_by("sequence").values_list("logical_page_revision_id", flat=True))
    second = propose_region_sequence(
        file.pk,
        edition_id=first.edition_id,
        expected_edition_number=1,
        expected_file_revision=file.revision,
        source_version_id=file.source_version_id,
        region_revision_ids=[regions[1].pk, other_revision.pk],
    )
    assert second.number == 2
    assert list(first.references.order_by("sequence").values_list("logical_page_revision_id", flat=True)) == first_ids
    assert [ref.logical_page_revision.region_revision_id for ref in second.references.order_by("sequence")] == [
        regions[1].pk,
        other_revision.pk,
    ]
    assert m.ContentConfirmation.objects.count() == 0


@pytest.mark.django_db
def test_region_content_post_requires_csrf_and_saves_only_unconfirmed_proposal(region_preview, client):  # noqa: F811
    file, regions, _ = region_preview
    arrangement = c.Arrangement.objects.create(work=c.Work.objects.create(title="Synthetic explicit UI"))
    part = c.Part.objects.create(instrument=c.InstrumentVariant.objects.create(name="Synthetic UI part"), code="1")
    edition = m.ContentEdition.objects.create(arrangement=arrangement, part=part)
    url = reverse("archive_review_detail", args=[file.pk])
    data = {
        "action": "region_content",
        "edition": str(edition.pk),
        "expected_edition_number": 0,
        "expected_file_revision": file.revision,
        "source_version_id": str(file.source_version_id),
        "region": [str(regions[1].pk), "", str(regions[1].pk)],
    }
    strict = Client(enforce_csrf_checks=True)
    strict.force_login(get_user_model().objects.get(pk=client.session.get("_auth_user_id")))
    assert strict.post(url, data).status_code == 403
    response = client.get(url)
    assert response.status_code == 200
    assert b"region_content" in response.content
    assert client.post(url, data).status_code == 302
    proposal = edition.revisions.get()
    assert proposal.references.count() == 2
    assert m.ContentInspection.objects.count() == m.ContentConfirmation.objects.count() == 0
    assert m.ReviewInspection.objects.count() == 0
    assert client.post(url, data).status_code == 302
    assert edition.revisions.count() == 1
