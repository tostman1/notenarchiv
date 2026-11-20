"""German job UI: authentication, CSRF, bounded lists and private-data exclusion."""

from uuid import uuid4

import pytest
from django.test import Client
from django.urls import reverse

from apps.jobs.models import Job, WorkerLease
from apps.jobs.services import queue


@pytest.fixture
def user_client(db, django_user_model, client):
    client.force_login(django_user_model.objects.create_user("synthetic-jobs"))
    WorkerLease.objects.get_or_create(pk=1)
    return client


@pytest.mark.django_db
@pytest.mark.parametrize("mode", [False, True])
def test_jobs_are_business_routes_in_both_modes(client, settings, mode):
    settings.DEBUG_MODE = mode
    job = Job.objects.create(kind="OCR")
    for url in (reverse("job_list"), reverse("job_detail", args=[job.pk]), reverse("job_cancel", args=[job.pk])):
        response = client.get(url)
        assert response.status_code == 302 and response.url.startswith("/login/")


def test_empty_list_and_unavailable_worker_are_honest(user_client):
    response = user_client.get(reverse("job_list"))
    body = response.content.decode()
    assert response.status_code == 200
    assert "Keine Aufträge vorhanden." in body and "Hintergrunddienst nicht verfügbar" in body
    assert "no-store" in response["Cache-Control"]
    queue.acquire_worker()
    assert "Hintergrunddienst verfügbar" in user_client.get(reverse("job_list")).content.decode()


def test_pagination_filters_progress_and_sanitized_errors(user_client):
    for index in range(27):
        Job.objects.create(kind="OCR", progress=index, payload={"private": "synthetic-private-ocr"})
    failed = Job.objects.create(kind="GENERATE", status="FAILED", error_code="<script>synthetic-private-error</script>")
    response = user_client.get(reverse("job_list"))
    assert len(response.context["page"]) == 25
    body = response.content.decode()
    assert "synthetic-private" not in body and "Fehlgeschlagen" in body
    filtered = user_client.get(reverse("job_list"), {"status": "FAILED", "kind": "GENERATE"})
    assert len(filtered.context["page"]) == 1
    detail = user_client.get(reverse("job_detail", args=[failed.pk])).content.decode()
    assert "synthetic-private" not in detail and "Ein technischer Fehler" in detail
    assert user_client.get(reverse("job_list"), {"status": "injected"}).status_code == 400
    assert user_client.get(reverse("job_detail", args=[uuid4()])).status_code == 404


def test_cancel_requires_post_csrf_and_never_retries_print(user_client, django_user_model):
    job = Job.objects.create(kind="PRINT", status="REVIEW_REQUIRED", error_code="PRINT_ACCEPTANCE_UNKNOWN")
    strict = Client(enforce_csrf_checks=True)
    strict.force_login(django_user_model.objects.get(username="synthetic-jobs"))
    url = reverse("job_cancel", args=[job.pk])
    assert strict.get(url).status_code == 405
    assert strict.post(url).status_code == 403
    strict.get(reverse("job_detail", args=[job.pk]))
    # Terminal pages have no cancel form/token; take CSRF from an active job.
    queued = Job.objects.create(kind="OCR")
    strict.get(reverse("job_detail", args=[queued.pk]))
    token = strict.cookies["notenarchiv_csrftoken"].value
    assert strict.post(url, {"csrfmiddlewaretoken": token}).status_code == 302
    job.refresh_from_db()
    assert job.status == "REVIEW_REQUIRED" and job.attempt == 0
    assert strict.post(reverse("job_cancel", args=[queued.pk]), {"csrfmiddlewaretoken": token}).status_code == 302
    queued.refresh_from_db()
    assert queued.status == "CANCELLED"
    body = strict.get(reverse("job_detail", args=[job.pk])).content.decode()
    assert "keine automatische Wiederholung" in body
