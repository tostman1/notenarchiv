"""Existing single-heavy-job queue drives incremental immutable OCR evidence."""

from pathlib import Path
from uuid import UUID

from django.conf import settings
from django.core.exceptions import ValidationError

from apps.archive import models as m
from apps.archive import recognition
from apps.archive.preview_services import preview_bytes, preview_file
from apps.jobs.models import Job
from apps.jobs.services import queue
from apps.jobs.services.lifecycle import ReviewRequired
from core import files
from core.ocr import Engine, Profile
from core.page_geometry import PageGeometry
from core.pdf.recovery import prune
from core.pdf.types import SourcePageGeometry


def validate(payload):
    if set(payload) != {"file_id"}:
        raise ValueError("Invalid OCR payload")
    return {"file_id": str(UUID(payload["file_id"]))}


def request(file_id, *, using="default"):
    # Same provenance/availability gate as actual PDF inspection, including
    # confirmed unchanged versions: OCR never revokes or changes approval.
    file = preview_file(file_id, using=using)
    if file.kind != "BASE":
        raise ValidationError("OCR requires an unchanged source publication.")
    existing = (
        Job.objects.using(using)
        .filter(kind="OCR", status__in=["QUEUED", "RUNNING"], payload={"file_id": str(file_id)})
        .first()
    )
    return existing or queue.enqueue("OCR", {"file_id": str(file_id)}, using=using)


def run(context):
    file = preview_file(context.payload["file_id"], using=context.using)
    data = preview_bytes(file)
    if file.kind != "BASE":
        raise ValidationError("OCR requires an unchanged source publication.")
    root = Path(settings.DIAGNOSTIC_LOG_DIR).parent / "ocr-scratch"
    root.mkdir(mode=0o700, exist_ok=True)
    # A terminated worker may have left an active/unproven native process.
    # Never delete its workspace or accumulate more scratch behind that marker.
    if any(root.iterdir()):
        raise ReviewRequired("OCR scratch requires process ownership review.")
    engine = Engine(
        root,
        "/usr/bin/tesseract",
        "/usr/share/tessdata",
        profile=Profile(languages=settings.OCR_LANGUAGES, dpi=settings.OCR_DPI, timeout=settings.OCR_TIMEOUT_SECONDS),
        checkpoint=context.check_cancelled,
        runtime_manifest="/lib/apk/db/installed",
    )
    rules = recognition.build_rule_set(context.using).version
    count = len(file.source_version.page_info)
    if not 1 <= count <= 500:
        raise ValidationError("OCR document page limit exceeded.")
    inspection = engine.processor.inspect(data, include_source_geometry=True)
    if len(inspection.pages) != count:
        raise ValidationError("OCR source page count mismatch.")
    for page in range(count):
        context.checkpoint(progress=page * 100 // count)
        # Whole-page boxes use retained original source geometry. The engine
        # accepts explicit region/revision inputs for subsequent logical workflows.
        # Exact source geometry comes from this immutable version, never from a
        # mutable current logical interpretation or a legacy reconstructed box.
        geometry = PageGeometry.from_source_page(
            SourcePageGeometry(inspection.pages[page], inspection.original_crop_boxes[page])
        )
        bounds = list(geometry.effective_points)
        key = engine.cache_key(file.sha256, page=page, bounds=bounds, orientation=0, revision=1, rules=rules)
        evidence = (
            m.OcrPageEvidence.objects.using(context.using)
            .filter(source_version=file.source_version, cache_key=key)
            .first()
        )
        if evidence is None:
            result = engine.recognize_page(data, page=page, bounds=bounds, rules=rules)
            evidence = context.commit_metadata(
                lambda key=key, page=page, result=result: m.OcrPageEvidence.objects.using(context.using).create(
                    source_version_id=file.source_version_id, cache_key=key, page=page, evidence=result
                )
            )
        context.commit_metadata(
            lambda evidence=evidence: recognition.record_candidate(
                file.source_version_id,
                filename=file.source_version.source_file.relative_path,
                text_lines=recognition.ocr_lines(evidence.evidence["words"]),
                ocr_evidence=evidence,
                using=context.using,
            )
        )
    context.checkpoint(progress=100)


def recover_cleanup(context):
    """Prune under dead-worker authority; markers never prove child termination."""
    context.checkpoint()
    parent = Path(settings.DIAGNOSTIC_LOG_DIR).parent
    if not (parent / "ocr-scratch").exists():
        return
    with files.Root(parent, writable=True) as root:
        prune(root, "ocr-scratch", ocr=True)
    context.checkpoint()


def register():
    queue.HANDLERS[Job.Kind.OCR] = queue.Handler(
        validate, run, idempotent=True, max_attempts=3, recover_cleanup=recover_cleanup
    )
