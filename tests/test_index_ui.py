"""Index UI authentication, CSRF, bounded status and no marker-only success."""

import hashlib
from uuid import uuid4, uuid5

import pytest
from django.test import Client
from django.urls import reverse

from apps.archive import models as m
from apps.archive.index_presentation import json_published
from apps.archive.indexing import queue_index
from apps.archive.status import _content
from apps.jobs.models import Job, OperationIntent


@pytest.fixture
def index_client(db, client, django_user_model):
    client.force_login(django_user_model.objects.create_user("synthetic-index-user"))
    return client


@pytest.mark.django_db
def test_index_routes_require_authentication_and_post_csrf(client, django_user_model):
    for name in ("archive_index", "archive_index_start", "archive_review_queue"):
        assert client.get(reverse(name)).status_code == 302
    strict = Client(enforce_csrf_checks=True)
    strict.force_login(django_user_model.objects.create_user("synthetic-index-csrf"))
    assert strict.get(reverse("archive_index_start")).status_code == 405
    assert strict.post(reverse("archive_index_start"), {"confirm": "on"}).status_code == 403
    strict.get(reverse("archive_index"))
    token = strict.cookies["notenarchiv_csrftoken"].value
    response = strict.post(reverse("archive_index_start"), {"confirm": "on", "csrfmiddlewaretoken": token})
    assert response.status_code == 302 and Job.objects.get().kind == "INDEX_SCAN"


def test_selected_and_all_actions_reuse_backend_and_validate_paths(index_client):
    assert (
        index_client.post(reverse("archive_index_start"), {"folder": "Synthetic", "confirm": "on"}).status_code == 302
    )
    assert m.IndexScan.objects.get().selected_path == "Synthetic"
    assert index_client.post(reverse("archive_index_start"), {"confirm": "on"}).status_code == 400
    for path in ("../raw", "/absolute", "a\\b"):
        assert index_client.post(reverse("archive_index_start"), {"folder": path, "confirm": "on"}).status_code == 400
    assert index_client.post(reverse("archive_index_start"), {"folder": "Other"}).status_code == 400
    assert Job.objects.count() == 1
    Job.objects.update(status="CANCELLED")
    assert index_client.post(reverse("archive_index_start"), {"confirm": "on"}).status_code == 302
    assert m.IndexScan.objects.filter(selected_path="").count() == 1


def test_overview_review_counts_pagination_and_escaped_source_names(index_client, archive):
    folder, _version, _file, _data = archive
    for number in range(26):
        m.SourceFolder.objects.create(relative_path=f"Synthetic-{number}")
    response = index_client.get(reverse("archive_index"))
    assert response.status_code == 200 and len(response.context["page"]) == 25
    assert response.context["pending_count"] == 1
    assert "Hintergrunddienst nicht verfügbar" in response.content.decode()
    assert "no-store" in response["Cache-Control"]
    assert index_client.get(reverse("archive_index_folder", args=[folder.pk])).status_code == 200
    assert index_client.get(reverse("archive_index_folder", args=[uuid4()])).status_code == 404
    response = index_client.get(reverse("archive_review_queue"), {"folder": str(folder.pk)})
    assert response.context["page"].paginator.count == 1 and "keine Freigabe" in response.content.decode()
    assert index_client.get(reverse("archive_review_queue"), {"folder": "../escape"}).status_code == 404


def test_json_is_authoritative_and_requires_completed_job_receipt_and_matching_bytes(index_client, settings, tmp_path):
    settings.STATUS_DIR = tmp_path / "status"
    settings.STATUS_DIR.mkdir()
    job = queue_index()
    folder = m.SourceFolder.objects.get(relative_path="")
    record = m.IndexFolder.objects.create(scan=job.index_scan, folder=folder, snapshot={"folder_id": str(folder.pk)})
    (settings.STATUS_DIR / "_INDIZIERT_BITTE_PRUEFEN.txt").write_text("Synthetic marker only")
    assert not json_published(record)
    Job.objects.filter(pk=job.pk).update(status="SUCCEEDED", attempt=1)
    m.IndexScan.objects.filter(pk=record.scan_id).update(completed=True)
    data = _content(record, "INDEXSTATUS.json")
    (settings.STATUS_DIR / "INDEXSTATUS.json").write_bytes(data)
    record = m.IndexFolder.objects.select_related("scan__job").get(pk=record.pk)
    assert not json_published(record)
    OperationIntent.objects.create(
        job=job,
        key="index-status:" + str(uuid5(record.pk, "INDEXSTATUS.json")),
        attempt=1,
        state="APPLIED",
        payload={
            "record_id": str(record.pk),
            "name": "INDEXSTATUS.json",
            "path": "INDEXSTATUS.json",
            "sha256": hashlib.sha256(data).hexdigest(),
            "size": len(data),
        },
        result={"sha256": hashlib.sha256(data).hexdigest(), "size": len(data)},
    )
    assert json_published(record)
    (settings.STATUS_DIR / "INDEXSTATUS.json").write_bytes(b"Synthetic external change")
    assert not json_published(record)
    response = index_client.get(reverse("archive_index_folder", args=[folder.pk]))
    assert "nicht als erfolgreich" in response.content.decode()


def test_error_codes_and_job_cancellation_are_visible_without_private_payload(index_client):
    job = queue_index()
    m.IndexScan.objects.filter(job=job).update(error_code="INVENTORY_FAILED")
    Job.objects.filter(pk=job.pk).update(
        status="FAILED", error_code="HANDLER_FAILED", payload={"secret": "synthetic-private"}
    )
    body = index_client.get(reverse("archive_index")).content.decode()
    assert "Fehlgeschlagen" in body and "Ordnerinventar nicht lesbar" in body and "synthetic-private" not in body
