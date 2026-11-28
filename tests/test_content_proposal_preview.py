"""Inspection previews use persisted proposal order, not mutable UI selection."""

import pytest
from django.contrib.auth import get_user_model
from django.http import Http404
from django.test import Client
from django.urls import reverse

from apps.archive import models as m
from apps.archive.content_geometry_services import append_region
from apps.archive.content_preview_services import proposal_preview
from tests.test_region_preview import region_preview  # noqa: F401
from tests.test_region_sequence_services import propose


@pytest.mark.django_db
def test_proposal_preview_pins_occurrences_and_history(region_preview, monkeypatch):  # noqa: F811
    file, regions, _ = region_preview
    revision = propose(file, [regions[1], regions[1]])
    append_region(regions[1].region_id, expected_number=2, bounds_points=[100, 0, 180, 180])
    captured = []

    def render(publication, identifiers):
        captured.extend(identifiers)
        assert publication.pk == file.pk
        return b"synthetic-preview"

    monkeypatch.setattr("apps.archive.content_preview_services.region_sequence", render)
    assert proposal_preview(file, revision.pk) == b"synthetic-preview"
    assert captured == [regions[1].pk, regions[1].pk]
    assert m.ContentInspection.objects.count() == m.ContentConfirmation.objects.count() == 0


@pytest.mark.django_db
def test_proposal_preview_rejects_wrong_publication_pin(region_preview):  # noqa: F811
    file, regions, _ = region_preview
    revision = propose(file, [regions[1]])
    file.revision += 1
    with pytest.raises(Http404):
        proposal_preview(file, revision.pk)


@pytest.mark.django_db
def test_saved_proposal_endpoints_are_private_and_do_not_attest_review(region_preview, client):  # noqa: F811
    file, regions, _ = region_preview
    revision = propose(file, [regions[1], regions[1]])
    viewer = reverse("archive_preview:content_proposal_viewer", args=[file.pk, revision.pk])
    document = reverse("archive_preview:content_proposal_document", args=[file.pk, revision.pk])
    response = client.get(viewer)
    assert response.status_code == 200
    assert revision.fingerprint in response.content.decode()
    assert response.context["sequence_count"] == 2
    assert response.context["export_document_url"] == document
    response = client.get(document)
    assert response.status_code == 200 and response.content.startswith(b"%PDF-")
    assert response["Cache-Control"] == "private, no-store"
    assert response["Content-Security-Policy"] == "sandbox; default-src 'none'"
    assert response["Content-Disposition"].startswith("attachment;")
    assert client.post(document).status_code == 405
    assert m.ContentInspection.objects.count() == m.ContentConfirmation.objects.count() == 0
    client.logout()
    assert client.get(viewer).status_code == client.get(document).status_code == 302


@pytest.mark.django_db
def test_saved_proposal_document_rejects_changed_bytes(region_preview, client):  # noqa: F811
    file, regions, target = region_preview
    revision = propose(file, [regions[1]])
    target.write_bytes(b"synthetic-corruption")
    response = client.get(reverse("archive_preview:content_proposal_document", args=[file.pk, revision.pk]))
    assert response.status_code == 404
    assert m.ContentInspection.objects.count() == m.ContentConfirmation.objects.count() == 0


@pytest.mark.django_db
def test_review_lists_only_pinned_compatible_saved_proposals(region_preview, client):  # noqa: F811
    file, regions, _ = region_preview
    revision = propose(file, [regions[1], regions[1]])
    response = client.get(reverse("archive_review_detail", args=[file.pk]))
    assert response.status_code == 200
    assert [item.pk for item in response.context["content_proposals"]] == [revision.pk]
    url = reverse("archive_preview:content_proposal_viewer", args=[file.pk, revision.pk])
    assert url in response.content.decode()
    file.revision += 1
    file.save(update_fields=["revision"])
    response = client.get(reverse("archive_review_detail", args=[file.pk]))
    assert response.context["content_proposals"] == []
    assert m.ContentInspection.objects.count() == m.ContentConfirmation.objects.count() == 0


@pytest.mark.django_db
def test_inspection_requires_csrf_explicit_attestation_and_exact_fingerprint(region_preview, client):  # noqa: F811
    file, regions, _ = region_preview
    revision = propose(file, [regions[1], regions[1]])
    viewer = reverse("archive_preview:content_proposal_viewer", args=[file.pk, revision.pk])
    action = reverse("archive_preview:content_proposal_inspect", args=[file.pk, revision.pk])
    strict = Client(enforce_csrf_checks=True)
    strict.force_login(get_user_model().objects.get(pk=client.session["_auth_user_id"]))
    payload = {"fingerprint": revision.fingerprint, "visually_reviewed": "on"}
    assert strict.post(action, payload).status_code == 403
    assert client.get(action).status_code == 405
    client.get(viewer)
    assert m.ContentInspection.objects.count() == 0
    client.post(action, {"fingerprint": revision.fingerprint})
    client.post(action, {"fingerprint": "0" * 64, "visually_reviewed": "on"})
    assert m.ContentInspection.objects.count() == 0
    response = client.post(action, payload)
    assert response.status_code == 302
    inspection = m.ContentInspection.objects.get()
    assert inspection.revision_id == revision.pk and inspection.fingerprint == revision.fingerprint
    assert inspection.visually_reviewed
    assert m.ContentConfirmation.objects.count() == 0
    assert m.ReviewInspection.objects.count() == m.ArchiveProposal.objects.count() == 0


@pytest.mark.django_db
def test_inspection_rejects_changed_region_and_corrupt_source(region_preview, client):  # noqa: F811
    file, regions, target = region_preview
    revision = propose(file, [regions[1]])
    action = reverse("archive_preview:content_proposal_inspect", args=[file.pk, revision.pk])
    payload = {"fingerprint": revision.fingerprint, "visually_reviewed": "on"}
    append_region(regions[1].region_id, expected_number=2, bounds_points=[100, 0, 180, 180])
    assert client.post(action, payload).status_code == 302
    assert m.ContentInspection.objects.count() == 0
    target.write_bytes(b"corrupt synthetic input")
    assert client.post(action, payload).status_code == 302
    assert m.ContentInspection.objects.count() == m.ContentConfirmation.objects.count() == 0


@pytest.mark.django_db
def test_inspection_verifies_bytes_for_current_region_proposal(region_preview, client):  # noqa: F811
    file, regions, target = region_preview
    revision = propose(file, [regions[1]])
    target.write_bytes(b"corrupt current synthetic input")
    action = reverse("archive_preview:content_proposal_inspect", args=[file.pk, revision.pk])
    response = client.post(action, {"fingerprint": revision.fingerprint, "visually_reviewed": "on"})
    assert response.status_code == 302
    assert m.ContentInspection.objects.count() == m.ContentConfirmation.objects.count() == 0
