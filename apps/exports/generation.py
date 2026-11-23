"""Personal reading artifacts from pinned inputs, fenced no-clobber publication."""

import hashlib
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError

from apps.exports.models import ExportArtifact, GenerationRun
from apps.exports.snapshot_services import load_pinned_inputs, validate_job_payload
from apps.jobs.models import Job
from apps.jobs.services import lifecycle, queue
from core import files, preview
from core.pdf import Processor
from core.pdf.staging import stage_bytes


def personal_pieces(snapshot, pins, person_id, checkpoint=lambda: None):
    payload = snapshot.payload
    cells = {cell["position_id"]: cell for cell in payload["cells"] if cell["participant_id"] == str(person_id)}
    selected = {str(pin.position_id): pin for pin in pins if pin.participant_id == person_id}
    pieces = []
    for position in payload["positions"]:
        checkpoint()
        cell = cells[position["id"]]
        state = "RESERVE" if cell["status"] == "RESERVE" else "MISSING" if cell["status"] == "MISSING" else "MUSIC"
        data = None
        if state == "MUSIC":
            pin = selected[position["id"]]
            data = preview.snapshot(
                settings.CURATED_DIR if cell["root_kind"] == "CLEAN" else settings.PROCESSED_DIR,
                cell["relative_path"],
                maximum=min(settings.PDF_MAX_BYTES, 104_857_600),
                sha256=pin.sha256,
                size=pin.byte_size,
            )
        elif state == "MISSING" and f"{position['id']}:{person_id}" not in snapshot.acknowledgements:
            raise ValidationError("Missing placeholder lacks authorization")
        pieces.append({"number": position["order"], "title": position["title"], "state": state, "data": data})
    return pieces


def run(context):
    snapshot, pins = load_pinned_inputs(context.payload["snapshot_id"], checkpoint=context.checkpoint)
    generation = snapshot.run
    if generation.job_id != context.job_id or snapshot.kind != "FULL":
        raise ValidationError("Unsupported or foreign generation authorization")
    scratch = Path(settings.DIAGNOSTIC_LOG_DIR).parent / "generation-scratch"
    scratch.mkdir(mode=0o700, exist_ok=True)
    processor = Processor(scratch, checkpoint=context.checkpoint)
    with files.Root(settings.EXPORT_DIR, writable=True) as root:
        for index, person in enumerate(snapshot.payload["participants"]):
            context.checkpoint(min(90, index * 90 // len(snapshot.payload["participants"])))
            existing = generation.artifacts.filter(participant_id=person["id"]).first()
            if existing:
                files.verify_published(
                    root,
                    existing.relative_path,
                    sha256=existing.sha256,
                    size=existing.byte_size,
                    checkpoint=context.checkpoint,
                )
                continue
            person_pin = snapshot.participants.get(participant_id=person["id"])
            pieces = personal_pieces(snapshot, pins, person_pin.participant_id, context.checkpoint)
            options = snapshot.payload["options"]
            size = (
                (options["width_mm"] * 72 / 25.4, options["height_mm"] * 72 / 25.4)
                if options["layout"] == "MARCHBOOK"
                else (595.2756, 841.8898)
            )
            data = processor.compose(
                pieces,
                project=snapshot.payload["project_name"],
                participant=person["name"],
                assignment=str(person["part"]),
                cover=options["cover_enabled"],
                page_size=size,
            )
            # Person UUID supplies stable stage identity; run directory protects history.
            stage_path = f".staging/{person_pin.pk.hex}/attempt-{context.attempt_number}.pdf"
            if root.exists(stage_path):
                raise lifecycle.ReviewRequired("Existing staging file requires inspection")
            stage, info = stage_bytes(root, stage_path, data, processor, context.checkpoint)
            path = f"Projekte/{snapshot.project_id}/run-{generation.pk}/Personen/{person['id']}/Lese-PDF.pdf"
            manifest = {
                "snapshot": snapshot.sha256,
                "page_count": len(info.pages),
                "geometry_sha256": hashlib.sha256(repr(info.pages).encode()).hexdigest(),
                "position_count": len(pieces),
            }
            payload = {
                "run": str(generation.pk),
                "person": person["id"],
                "path": path,
                "stage": stage.path,
                "sha256": stage.sha256,
                "size": stage.size,
                "manifest": manifest,
            }
            with root.parent(path, create=True):
                pass

            def apply(stage=stage, path=path):
                try:
                    files.publish(root, stage, path)
                except files.FileError as exc:
                    if exc.code in {"DESTINATION_EXISTS", "STAGING_CHANGED", "UNSAFE_DESTINATION"}:
                        raise lifecycle.NoEffect("Publication did not occur") from None
                    raise
                return {"sha256": stage.sha256, "size": stage.size}

            context.publish("artifact:" + person["id"], payload, apply)
            files.release_stage(root, stage.path, path)
    if generation.artifacts.count() != len(snapshot.payload["participants"]):
        raise ValidationError("Incomplete participant artifact inventory")


def acknowledge(context, intent):
    payload = intent.payload
    run = GenerationRun.objects.get(pk=payload["run"], job_id=context.job_id)
    if intent.result != {"sha256": payload["sha256"], "size": payload["size"]}:
        raise ValidationError("Invalid output receipt")
    ExportArtifact.objects.get_or_create(
        run=run,
        participant_id=payload["person"],
        defaults={
            "relative_path": payload["path"],
            "sha256": payload["sha256"],
            "byte_size": payload["size"],
            "manifest": payload["manifest"],
            "intent": intent,
        },
    )


def reconcile(context, intent):
    payload = intent.payload
    with files.Root(settings.EXPORT_DIR, writable=True) as root:
        if not root.exists(payload["path"]):
            return "ABANDONED", {}
        files.verify_published(
            root,
            payload["path"],
            sha256=payload["sha256"],
            size=payload["size"],
            staged_path=payload["stage"],
            checkpoint=context.checkpoint,
            durable=True,
        )
        return "APPLIED", {"sha256": payload["sha256"], "size": payload["size"]}


def register():
    queue.HANDLERS[Job.Kind.GENERATE] = queue.Handler(
        validate_job_payload, run, idempotent=True, max_attempts=3, reconcile=reconcile, acknowledge=acknowledge
    )
