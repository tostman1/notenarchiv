"""Existing single-heavy-job queue drives incremental immutable OCR evidence."""

import math
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
from core.page_geometry import DisplayTransform, PageGeometry
from core.pdf.recovery import prune
from core.pdf.types import SourcePageGeometry


def validate(payload):
    if not isinstance(payload, dict) or set(payload) not in ({"file_id"}, {"file_id", "selection"}):
        raise ValueError("Invalid OCR payload")
    result = {"file_id": str(UUID(payload["file_id"]))}
    if "selection" in payload:
        selection = payload["selection"]
        if not isinstance(selection, dict) or set(selection) != {"page", "box"}:
            raise ValueError("Invalid OCR selection")
        page, box = selection["page"], selection["box"]
        if type(page) is not int or not 0 <= page < 500:
            raise ValueError("Invalid OCR page")
        if not isinstance(box, list) or len(box) != 4:
            raise ValueError("Invalid OCR rectangle")
        if any(type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 1 for v in box):
            raise ValueError("Invalid OCR rectangle")
        if box[0] >= box[2] or box[1] >= box[3]:
            raise ValueError("Invalid OCR rectangle")
        result["selection"] = {"page": page, "box": list(box)}
    return result


def request(file_id, *, selection=None, using="default"):
    # Same provenance/availability gate as actual PDF inspection, including
    # confirmed unchanged versions: OCR never revokes or changes approval.
    file = preview_file(file_id, using=using)
    if file.kind != "BASE":
        raise ValidationError("OCR requires an unchanged source publication.")
    payload = {"file_id": str(file.pk)}
    if selection is not None:
        payload["selection"] = selection
    payload = validate(payload)
    if selection is not None and payload["selection"]["page"] >= len(file.source_version.page_info):
        raise ValidationError("OCR page does not exist.")
    existing = Job.objects.using(using).filter(kind="OCR", status__in=["QUEUED", "RUNNING"], payload=payload).first()
    return existing or queue.enqueue("OCR", payload, using=using)


def selection_bounds(geometry, box):
    """Displayed top-left fractions become canonical physical source points."""
    width, height = geometry.display_points
    transform = DisplayTransform(geometry, 1)
    corners = [transform.to_points([x * width, y * height]) for x in (box[0], box[2]) for y in (box[1], box[3])]
    bounds = [
        min(p[0] for p in corners),
        min(p[1] for p in corners),
        max(p[0] for p in corners),
        max(p[1] for p in corners),
    ]
    return list(geometry.region(bounds).bounds)


def run(context):
    payload = validate(context.payload)
    file = preview_file(payload["file_id"], using=context.using)
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
    selection = payload.get("selection")
    if selection is not None and selection["page"] >= count:
        raise ValidationError("OCR page does not exist.")
    pages = [selection["page"]] if selection else range(count)
    for position, page in enumerate(pages):
        context.checkpoint(progress=position * 100 // len(pages))
        # Whole-page boxes use retained original source geometry. The engine
        # accepts explicit region/revision inputs for subsequent logical workflows.
        # Exact source geometry comes from this immutable version, never from a
        # mutable current logical interpretation or a legacy reconstructed box.
        geometry = PageGeometry.from_source_page(
            SourcePageGeometry(inspection.pages[page], inspection.original_crop_boxes[page])
        )
        bounds = selection_bounds(geometry, selection["box"]) if selection else list(geometry.effective_points)
        key = engine.cache_key(file.sha256, page=page, bounds=bounds, orientation=0, revision=1, rules=rules)
        evidence = (
            m.OcrPageEvidence.objects.using(context.using)
            .filter(source_version=file.source_version, cache_key=key)
            .first()
        )
        if evidence is None:
            result = engine.recognize_page(data, page=page, bounds=bounds, rules=rules)
            result["display_box"] = selection["box"] if selection else [0, 0, 1, 1]
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
