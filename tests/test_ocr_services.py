"""Durable OCR evidence reuses the existing queue without musical approval."""

import hashlib
import os
from types import SimpleNamespace

import pytest
from django.core.exceptions import ValidationError

from apps.archive import models as m
from apps.archive import ocr_services as service
from apps.archive import recognition
from apps.jobs.models import Job
from tests.test_archive_workflow import reviewed_inputs  # noqa: F401


def test_immutable_evidence_and_candidates_do_not_approve(archive):
    _, version, file, _ = archive
    key = "1" * 64
    evidence = m.OcrPageEvidence.objects.create(
        source_version=version,
        cache_key=key,
        page=0,
        evidence={
            "sha256": version.sha256,
            "cache_key": key,
            "page": 0,
            "rules": recognition.build_rule_set().version,
            "text_layer": "Other printed information",
            "words": [{"text": "Unknown musical title", "box": [10, 10, 80, 30], "confidence": 0.6}],
        },
    )
    before = (file.review_state, file.current_proposal_id, file.revision)
    candidate, _ = recognition.record_candidate(
        version.pk, filename="Scan.pdf", text_lines=["Unknown musical title"], ocr_evidence=evidence
    )
    again, _ = recognition.record_candidate(
        version.pk, filename="Scan.pdf", text_lines=["Unknown musical title"], ocr_evidence=evidence
    )
    assert candidate.pk == again.pk
    assert candidate.method == "OCR" and candidate.region["page"] == 0
    assert "Other printed information" in candidate.excerpt
    file.refresh_from_db()
    assert (file.review_state, file.current_proposal_id, file.revision) == before
    with pytest.raises(ValidationError, match="immutable"):
        evidence.save()


def test_request_uses_existing_queue_and_bounds_payload(archive, monkeypatch):
    _, _, file, _ = archive
    monkeypatch.setattr(service, "preview_file", lambda *a, **k: file)
    first = service.request(file.pk)
    assert service.request(file.pk).pk == first.pk
    assert first.kind == Job.Kind.OCR
    assert first.payload == {"file_id": str(file.pk)}
    with pytest.raises(ValueError):
        service.validate({"file_id": str(file.pk), "path": "untrusted"})


def test_reanalysis_preserves_confirmed_approval_and_rule_changes_require_review(reviewed_inputs):  # noqa: F811
    from tests.test_archive_workflow import confirm, draft

    _, version, file, actor, _, arrangement, parts = reviewed_inputs
    proposal = draft(file, actor, arrangement, parts[:1])
    confirm(file, proposal, actor)
    file.refresh_from_db()
    before = (file.review_state, file.revision, file.current_proposal_id)
    evidence = m.OcrPageEvidence.objects.create(
        source_version=version,
        cache_key="2" * 64,
        page=0,
        evidence={
            "sha256": version.sha256,
            "cache_key": "2" * 64,
            "page": 0,
            "rules": recognition.build_rule_set().version,
            "text_layer": "",
            "words": [],
        },
    )
    recognition.record_candidate(version.pk, filename="Scan.pdf", ocr_evidence=evidence)
    file.refresh_from_db()
    assert (file.review_state, file.revision, file.current_proposal_id) == before
    # Cached evidence from another rule context cannot silently become a current
    # recognition proposal. The stored earlier evidence remains unchanged.
    evidence.evidence = {**evidence.evidence, "rules": "obsolete-rule-context"}
    with pytest.raises(ValidationError):
        recognition.record_candidate(version.pk, filename="Scan.pdf", ocr_evidence=evidence)
    assert m.OcrPageEvidence.objects.get(pk=evidence.pk).evidence["rules"] == recognition.build_rule_set().version


def test_restart_reuses_committed_pages_and_preserves_review(archive, settings, tmp_path, monkeypatch):
    from core.pdf.types import DocumentInfo, PageInfo

    _, version, file, data = archive
    settings.DIAGNOSTIC_LOG_DIR = tmp_path / "logs"
    calls = []
    geometry = PageInfo((0, 0, 100, 100), (0, 0, 100, 100), 1, 0, 100, 100)
    # A synthetic single page uses no untrusted native OCR in this DB test.
    monkeypatch.setattr(service, "preview_file", lambda *a, **k: file)
    monkeypatch.setattr(service, "preview_bytes", lambda *a: data)

    class SyntheticEngine:
        def __init__(self, *a, **k):
            self.processor = SimpleNamespace(
                inspect=lambda *a, **k: DocumentInfo(
                    version.sha256, (geometry,), original_crop_boxes=((0, 0, 100, 100),)
                )
            )

        def cache_key(self, sha256, **kwargs):
            return hashlib.sha256(str(kwargs).encode()).hexdigest()

        def recognize_page(self, data, **kwargs):
            calls.append(kwargs["page"])
            return {
                "cache_key": self.cache_key(
                    version.sha256,
                    page=kwargs["page"],
                    bounds=kwargs["bounds"],
                    orientation=0,
                    revision=1,
                    rules=kwargs["rules"],
                ),
                "sha256": version.sha256,
                "page": kwargs["page"],
                "rules": kwargs["rules"],
                "text_layer": "",
                "words": [],
            }

    monkeypatch.setattr(service, "Engine", SyntheticEngine)
    progress = []
    context = SimpleNamespace(
        payload={"file_id": str(file.pk)},
        using="default",
        check_cancelled=lambda: None,
        checkpoint=lambda **k: progress.append(k["progress"]),
        commit_metadata=lambda action: action(),
    )
    service.run(context)
    service.run(context)
    assert calls == [0]
    assert m.OcrPageEvidence.objects.count() == 1
    assert m.RecognitionCandidate.objects.filter(method="OCR").count() == 1
    assert progress == [0, 100, 0, 100]
    abandoned = tmp_path / "ocr-scratch" / "pdf-abandoned"
    abandoned.mkdir()
    from apps.jobs.services.lifecycle import ReviewRequired

    with pytest.raises(ReviewRequired):
        service.run(context)


@pytest.mark.skipif(os.name != "posix", reason="Owned native scratch recovery requires server filesystem API")
def test_dead_worker_recovery_prunes_only_unmarked_owned_ocr_files(settings, tmp_path):
    from core import files

    settings.DIAGNOSTIC_LOG_DIR = tmp_path / "logs"
    stage = tmp_path / "ocr-scratch" / "pdf-abandoned"
    stage.mkdir(parents=True, mode=0o700)
    context = SimpleNamespace(checkpoint=lambda: None)
    for name in ("input.png", "result.tsv", "0.pdf", "request.json"):
        (stage / name).write_bytes(b"synthetic")
    service.recover_cleanup(context)
    assert not stage.exists()
    stage.mkdir(mode=0o700)
    (stage / "parser-active").write_bytes(b"")
    (stage / "input.png").write_bytes(b"synthetic")
    with pytest.raises(files.FileError):
        service.recover_cleanup(context)
    assert (stage / "input.png").exists()
    (stage / "parser-active").unlink()
    (stage / "input.png").unlink()
    (stage / "input.png").symlink_to(tmp_path / "not-owned")
    with pytest.raises(files.FileError):
        service.recover_cleanup(context)
