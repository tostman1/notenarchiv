"""Exact selected-region scheduling and private source image evidence."""

from types import SimpleNamespace

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from apps.archive import models as m
from apps.archive import ocr_services as services
from core.page_geometry import PageGeometry
from tests.test_preview import preview  # noqa: F401


@pytest.mark.parametrize(
    "rotation,expected",
    [(0, [0, 100, 50, 200]), (90, [0, 0, 50, 100]), (180, [50, 0, 100, 100]), (270, [50, 100, 100, 200])],
)
def test_displayed_selection_maps_exact_rotated_source(rotation, expected):
    geometry = PageGeometry([0, 0, 100, 200], [0, 0, 100, 200], rotation)
    assert services.selection_bounds(geometry, [0, 0, 0.5, 0.5]) == expected


def test_display_selection_preserves_userunit_and_off_origin_crop():
    geometry = PageGeometry([-50, -100, 250, 400], [-10, 20, 190, 320], 90, 2)
    assert services.selection_bounds(geometry, [0, 0, 1, 1]) == list(geometry.effective_points)
    assert services.selection_bounds(geometry, [0, 0, 0.5, 0.5]) == [-20, 40, 180, 340]


@pytest.mark.parametrize(
    "extra",
    [{"page": 0}, {"page": 501}, {"left": "nan"}, {"right": "inf"}, {"top": 80, "bottom": 20}],
)
def test_keyboard_selection_form_fails_closed(extra):
    from apps.archive.review_forms import OcrSelectionForm

    assert not OcrSelectionForm({"page": 1, "left": 0, "top": 0, "right": 100, "bottom": 100, **extra}).is_valid()


@pytest.mark.parametrize(
    "selection",
    [
        {"page": True, "box": [0, 0, 1, 1]},
        {"page": -1, "box": [0, 0, 1, 1]},
        {"page": 500, "box": [0, 0, 1, 1]},
        {"page": 0, "box": [0, 0, float("nan"), 1]},
        {"page": 0, "box": [0, 0, float("inf"), 1]},
        {"page": 0, "box": [0, 0, True, 1]},
        {"page": 0, "box": [0, 0, 0, 1]},
        {"page": 0, "box": [0, -0.1, 1, 1]},
        {"page": 0, "box": [1, 0, 0, 1]},
        {"page": 0, "box": [0, 0, 2, 1]},
        {"page": 0, "box": [0, 0, 1, 1], "path": "untrusted"},
    ],
)
def test_payload_rejects_invalid_selections(selection):
    with pytest.raises(ValueError):
        services.validate({"file_id": "00000000-0000-0000-0000-000000000001", "selection": selection})


def test_selected_requests_are_distinct_and_idempotent(archive, monkeypatch):
    _, _, file, _ = archive
    monkeypatch.setattr(services, "preview_file", lambda *a, **k: file)
    whole = services.request(file.pk)
    selected = services.request(file.pk, selection={"page": 0, "box": [0, 0, 0.5, 0.5]})
    assert selected.pk != whole.pk
    assert services.request(file.pk, selection=selected.payload["selection"]).pk == selected.pk
    with pytest.raises(ValidationError, match="page"):
        services.request(file.pk, selection={"page": 1, "box": [0, 0, 1, 1]})


def evidence(file):
    return m.OcrPageEvidence.objects.create(
        source_version=file.source_version,
        cache_key="3" * 64,
        page=0,
        evidence={
            "sha256": file.sha256,
            "cache_key": "3" * 64,
            "page": 0,
            "bounds": [0, 0, 100, 100],
            "orientation": 0,
        },
    )


def test_image_evidence_is_private_verified_and_read_only(preview, client, monkeypatch):  # noqa: F811
    from apps.archive import preview_services

    file, data, target = preview
    item = evidence(file)
    url = reverse("archive_preview:ocr_excerpt", kwargs={"file_id": file.pk, "evidence_id": item.pk})
    calls = []

    class SyntheticProcessor:
        def __init__(self, *a, **k):
            pass

        def logical_pages(self, inputs, selections):
            calls.append((inputs, selections))
            return b"synthetic logical page"

        def render(self, *a, **k):
            return b"synthetic PNG"

    monkeypatch.setattr(preview_services, "Processor", SyntheticProcessor)
    before = (file.revision, m.ReviewInspection.objects.count(), m.AuditEvent.objects.count())
    response = client.get(url)
    assert response.status_code == 200 and response.content == b"synthetic PNG"
    assert response["Cache-Control"] == "private, no-store"
    assert response["Content-Type"] == "image/png"
    assert response["X-Content-Type-Options"] == "nosniff"
    assert response["Cross-Origin-Resource-Policy"] == "same-origin"
    assert client.post(url).status_code == 405
    assert calls[0][0] == [data]
    assert calls[0][1][0]["bounds"] == [0, 0, 100, 100]
    assert target.read_bytes() == data
    file.refresh_from_db()
    assert before == (file.revision, m.ReviewInspection.objects.count(), m.AuditEvent.objects.count())
    target.write_bytes(b"corrupt")
    assert client.get(url).status_code == 404
    client.logout()
    assert client.get(url).status_code == 302


def test_foreign_source_evidence_cannot_be_previewed(preview, client):  # noqa: F811
    from apps.archive import services as archive_services

    file, _, _ = preview
    folder = m.SourceFolder.objects.create(relative_path="Other synthetic source")
    version, _ = archive_services.observe_version(
        folder.pk,
        "Other synthetic source/scan.pdf",
        sha256=file.sha256,
        byte_size=file.byte_size,
        mtime_ns=1000,
        pdf_state="VALID",
        page_info=file.source_version.page_info,
    )
    other = archive_services.register_base(version.pk, "_Ungeprueft/other.pdf")
    item = evidence(other)
    assert item.source_version_id != file.source_version_id
    url = reverse("archive_preview:ocr_excerpt", kwargs={"file_id": file.pk, "evidence_id": item.pk})
    assert client.get(url).status_code == 404


def test_exact_source_excerpt_runs_real_bounded_pdf_processor(preview, client):  # noqa: F811
    file, data, target = preview
    item = evidence(file)
    url = reverse("archive_preview:ocr_excerpt", kwargs={"file_id": file.pk, "evidence_id": item.pk})
    response = client.get(url)
    assert response.status_code == 200
    assert response.content.startswith(b"\x89PNG\r\n\x1a\n")
    assert target.read_bytes() == data


def test_incomplete_legacy_evidence_fails_closed(preview, client):  # noqa: F811
    file, _, _ = preview
    item = m.OcrPageEvidence.objects.create(
        source_version=file.source_version,
        cache_key="7" * 64,
        page=0,
        evidence={"sha256": file.sha256, "cache_key": "7" * 64, "page": 0},
    )
    url = reverse("archive_preview:ocr_excerpt", kwargs={"file_id": file.pk, "evidence_id": item.pk})
    assert client.get(url).status_code == 404


def test_selected_launch_requires_authentication_and_csrf_and_never_inspects(preview, client):  # noqa: F811
    from django.test import Client

    from apps.jobs.models import Job

    file, data, target = preview
    url = reverse("archive_review_detail", kwargs={"file_id": file.pk})
    payload = {"action": "ocr_selection", "page": "1", "left": "5", "top": "10", "right": "75", "bottom": "90"}
    before = m.ReviewInspection.objects.count()
    strict = Client(enforce_csrf_checks=True)
    # Use the authenticated session from the fixture without inventing a reviewer.
    strict.cookies = client.cookies.copy()
    assert strict.post(url, payload).status_code == 403
    response = client.post(url, payload)
    assert response.status_code == 302
    job = Job.objects.get(kind="OCR")
    assert job.payload["selection"] == {"page": 0, "box": [0.05, 0.10, 0.75, 0.90]}
    assert m.ReviewInspection.objects.count() == before
    assert target.read_bytes() == data
    file.refresh_from_db()
    assert file.review_state == "PENDING"
    assert client.post(url, {**payload, "left": "90", "right": "1"}).status_code == 302
    assert Job.objects.filter(kind="OCR").count() == 1
    client.logout()
    assert client.post(url, payload).status_code == 302
    assert Job.objects.filter(kind="OCR").count() == 1


def test_review_renders_bounded_escaped_image_evidence(preview, client):  # noqa: F811
    from apps.archive import recognition

    file, _, _ = preview
    item = m.OcrPageEvidence.objects.create(
        source_version=file.source_version,
        cache_key="8" * 64,
        page=0,
        evidence={
            "sha256": file.sha256,
            "cache_key": "8" * 64,
            "page": 0,
            "rules": recognition.build_rule_set().version,
            "text_layer": "",
            "bounds": [0, 0, 100, 100],
            "orientation": 0,
            "words": [{"text": "<script>unsafe</script>", "confidence": 0.5, "box": [1, 2, 3, 4]}] * 101,
        },
    )
    recognition.record_candidate(file.source_version_id, filename="synthetic.pdf", ocr_evidence=item)
    response = client.get(reverse("archive_review_detail", args=[file.pk]))
    assert response.status_code == 200
    html = response.content.decode()
    assert 'id="ocr-selection"' in html and 'value="ocr_selection"' in html
    assert reverse("archive_preview:ocr_excerpt", args=[file.pk, item.pk]) in html
    assert 'data-preview-page="1"' in html and 'loading="lazy"' in html
    assert "<script>unsafe</script>" not in html
    assert len(response.context["candidates"][0].ocr_words) == 100
    assert m.ReviewInspection.objects.count() == 0


@pytest.mark.parametrize("selected_page", [0, 1])
def test_job_ocr_uses_selected_geometry_and_retains_candidate_region(
    archive, monkeypatch, settings, tmp_path, selected_page
):
    from apps.archive import recognition
    from core.pdf.types import DocumentInfo, PageInfo

    _, version, file, data = archive
    file.source_version.page_info = file.source_version.page_info * 2
    settings.DIAGNOSTIC_LOG_DIR = tmp_path / "logs"
    monkeypatch.setattr(services, "preview_file", lambda *a, **k: file)
    monkeypatch.setattr(services, "preview_bytes", lambda *a: data)
    calls = []
    info = PageInfo((0, 0, 100, 200), (0, 0, 100, 200), 1, 0, 100, 200)

    class SyntheticEngine:
        def __init__(self, *a, **k):
            self.processor = SimpleNamespace(
                inspect=lambda *a, **k: DocumentInfo(
                    version.sha256, (info, info), original_crop_boxes=((0, 0, 100, 200), (0, 0, 100, 200))
                )
            )

        def cache_key(self, *a, **k):
            return "4" * 64

        def recognize_page(self, data, **kwargs):
            calls.append(kwargs)
            return {
                "sha256": version.sha256,
                "cache_key": "4" * 64,
                "page": kwargs["page"],
                "rules": recognition.build_rule_set().version,
                "words": [],
                "text_layer": "",
                "bounds": kwargs["bounds"],
                "orientation": 0,
            }

    monkeypatch.setattr(services, "Engine", SyntheticEngine)
    context = SimpleNamespace(
        payload={"file_id": str(file.pk), "selection": {"page": selected_page, "box": [0, 0, 0.5, 0.5]}},
        using="default",
        check_cancelled=lambda: None,
        checkpoint=lambda **k: None,
        commit_metadata=lambda action: action(),
    )
    services.run(context)
    services.run(context)
    assert len(calls) == 1 and calls[0]["bounds"] == [0, 100, 50, 200]
    assert calls[0]["page"] == selected_page
    assert m.RecognitionCandidate.objects.get(method="OCR").region["box"] == [0, 0, 0.5, 0.5]
    assert m.OcrPageEvidence.objects.get().evidence["display_box"] == [0, 0, 0.5, 0.5]
    assert m.OcrPageEvidence.objects.get().page == selected_page
