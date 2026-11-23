"""Snapshot-only composition with durable, fenced, no-clobber publication."""

import json
import os
import time
from contextlib import ExitStack, suppress
from dataclasses import asdict, replace
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError

from apps.exports.models import ExportArtifact, ExportCompletion, ExportPublication, ExportStage
from apps.exports.snapshot_services import load_pinned_inputs, validate_job_payload
from apps.jobs.models import Job
from apps.jobs.services import lifecycle, queue
from apps.projects.preflight_services import fingerprint
from core import files, preview
from core.naming import component
from core.pdf import Limits, Processor
from core.pdf.recovery import prune
from core.pdf.staging import stage_bytes

MAX_RUN_BYTES = 512 * 1024**2
MAX_RUN_SECONDS = 1800


def personal_pieces(snapshot, pins, person_id, checkpoint=lambda: None):
    cells = {c["position_id"]: c for c in snapshot.payload["cells"] if c["participant_id"] == str(person_id)}
    selected = {str(p.position_id): p for p in pins if p.participant_id == person_id}
    pieces, total = [], 0
    for position in snapshot.payload["positions"]:
        checkpoint()
        cell = cells[position["id"]]
        if cell["status"] not in {"RESERVE", "MISSING", "AVAILABLE", "SUBSTITUTED"}:
            raise ValidationError("Invalid pinned composition state")
        state = "RESERVE" if cell["status"] == "RESERVE" else "MISSING" if cell["status"] == "MISSING" else "MUSIC"
        data = None
        if state == "MUSIC":
            pin = selected[position["id"]]
            total += pin.byte_size
            if total > min(settings.PDF_MAX_BYTES, 104_857_600):
                raise ValidationError("Personal PDF input limit exceeded")
            data = preview.snapshot(
                settings.CURATED_DIR if cell["root_kind"] == "CLEAN" else settings.PROCESSED_DIR,
                cell["relative_path"],
                maximum=pin.byte_size,
                sha256=pin.sha256,
                size=pin.byte_size,
            )
        elif state == "MISSING" and f"{position['id']}:{person_id}" not in snapshot.acknowledgements:
            raise ValidationError("Missing placeholder lacks authorization")
        pieces.append({"number": position["order"], "title": position["title"], "state": state, "data": data})
    return pieces


def output_path(snapshot, person):
    project = "Projekt-" + component(snapshot.payload["project_name"], maximum=64) + "--" + snapshot.project_id.hex
    name = "Person-" + component(person["name"], maximum=64) + "--" + person["id"].replace("-", "")
    return f"Projekte/{project}/run-{snapshot.run.pk.hex}/Personen/{name}/Lese-PDF.pdf"


def _roots(stack):
    paths = [
        Path(getattr(settings, name)).absolute()
        for name in ("SOURCE_DIR", "CURATED_DIR", "PROCESSED_DIR", "EXPORT_DIR")
    ]
    paths.append(Path(settings.DIAGNOSTIC_LOG_DIR).parent.absolute())
    if any(a.is_relative_to(b) or b.is_relative_to(a) for i, a in enumerate(paths) for b in paths[:i]):
        raise files.FileError("OVERLAPPING_ROOTS")
    roots = [stack.enter_context(files.Root(p, writable=i >= 3)) for i, p in enumerate(paths)]
    if len({files.identity(os.fstat(r.fd)) for r in roots}) != len(roots):
        raise files.FileError("OVERLAPPING_ROOTS")
    return roots[3], roots[4]


def _processor(data_root, checkpoint):
    with data_root.parent(".staging/generation/placeholder", create=True):
        pass
    return Processor(
        data_root.path / ".staging/generation",
        checkpoint=checkpoint,
        limits=Limits(max_bytes=min(settings.PDF_MAX_BYTES, 104_857_600)),
    )


def _plan(context, snapshot, person):
    publication, _ = context.commit_metadata(
        lambda: ExportPublication.objects.get_or_create(
            run=snapshot.run, participant_id=person["id"], defaults={"relative_path": output_path(snapshot, person)}
        )
    )
    return publication


def _cleanup(context, publication, root):
    for number in range(1, context.attempt_number):
        if not publication.run.job.history.filter(number=number, status__in=["FAILED", "CANCELLED"]).exists():
            raise lifecycle.ReviewRequired("Unproven abandoned attempt")
        path = f".staging/{publication.pk.hex}/attempt-{number}.pdf"
        if root.exists(path):
            info = root.metadata(path)
            if info.st_uid != os.geteuid():
                raise files.FileError("UNSAFE_STAGING")
            files.discard_stage(root, path, files.identity(info))


def _existing(publication, root, checkpoint):
    artifact = ExportArtifact.objects.filter(run=publication.run, participant_id=publication.participant_id).first()
    if not artifact:
        return None
    artifact.full_clean()
    stage = publication.stages.get(attempt=artifact.intent.attempt)
    retained = stage.relative_path if root.exists(stage.relative_path) else None
    files.verify_published(
        root,
        artifact.relative_path,
        sha256=artifact.sha256,
        size=artifact.byte_size,
        staged_path=retained,
        checkpoint=checkpoint,
    )
    if retained:
        files.release_stage(root, retained, artifact.relative_path)
    return artifact


def _compose(context, snapshot, pins, person, processor, publication, root):
    person_id = snapshot.participants.get(participant_id=person["id"]).participant_id
    pieces = personal_pieces(snapshot, pins, person_id, processor.checkpoint)
    logical = [{k: p[k] for k in ("number", "title", "state")} for p in pieces]
    options = snapshot.payload["options"]
    size = (
        (options["width_mm"] * 72 / 25.4, options["height_mm"] * 72 / 25.4)
        if options["layout"] == "MARCHBOOK"
        else (595.2756, 841.8898)
    )
    dependencies = snapshot.payload["dependencies"]
    part = next(p for p in dependencies["parts"] if p["id"] == person["part"])
    instrument = next(p for p in dependencies["instruments"] if p["id"] == part["instrument_id"])
    assignment = f"{instrument['name']} {part['code']}"
    if person["role"]:
        role = next(r for r in dependencies["roles"] if r["id"] == person["role"])
        assignment += f" · {role['label']}"
    data = processor.compose(
        pieces,
        project=options["cover_title"] or snapshot.payload["project_name"],
        participant=person["name"],
        assignment=assignment,
        cover=options["cover_enabled"],
        page_size=size,
    )
    del pieces
    path = f".staging/{publication.pk.hex}/attempt-{context.attempt_number}.pdf"
    stage, info = stage_bytes(root, path, data, processor, processor.checkpoint)
    del data
    try:
        manifest = {
            "schema": 1,
            "renderer": "reading-v1",
            "kind": snapshot.kind,
            "snapshot_id": str(snapshot.pk),
            "snapshot_sha256": snapshot.sha256,
            "participant_id": person["id"],
            "participant_name": person["name"],
            "positions": logical,
            "inputs": [c for c in snapshot.payload["cells"] if c["participant_id"] == person["id"]],
            "pages": [asdict(p) for p in info.pages],
            "page_count": len(info.pages),
        }
        manifest = json.loads(json.dumps(manifest))
        recorded = context.commit_metadata(
            lambda: ExportStage.objects.create(
                publication=publication,
                attempt=context.attempt_number,
                sha256=stage.sha256,
                byte_size=stage.size,
                manifest=manifest,
            )
        )
        processor.checkpoint()
        with root.parent(publication.relative_path, create=True):
            pass

        def apply():
            try:
                files.publish(root, stage, publication.relative_path)
            except files.FileError as exc:
                if exc.code in {"DESTINATION_EXISTS", "STAGING_CHANGED", "UNSAFE_DESTINATION"}:
                    raise lifecycle.NoEffect("Publication did not occur") from None
                raise
            return recorded.receipt

        context.publish("artifact:" + publication.participant_id.hex, {"publication": str(publication.pk)}, apply)
        files.release_stage(root, stage.path, publication.relative_path)
    finally:
        with suppress(files.FileError, OSError):
            files.discard_stage(root, stage.path, files.identity(stage.info))


def inventory(run):
    artifacts = list(run.artifacts.select_related("intent").order_by("participant_id"))
    if {str(a.participant_id) for a in artifacts} != {p["id"] for p in run.snapshot.payload["participants"]}:
        raise ValidationError("Incomplete participant artifact inventory")
    for artifact in artifacts:
        artifact.full_clean()
    return [
        {
            "artifact": str(a.pk),
            "participant": str(a.participant_id),
            "path": a.relative_path,
            "sha256": a.sha256,
            "size": a.byte_size,
        }
        for a in artifacts
    ]


def is_complete(run):
    if run.job.status != "SUCCEEDED":
        return False
    try:
        completion = run.completion
        return completion.inventory == inventory(run) and completion.sha256 == fingerprint(completion.inventory)
    except (ExportCompletion.DoesNotExist, ValidationError, ExportStage.DoesNotExist):
        return False


def verified_complete(run):
    """Fail closed if any artifact in the published batch has become unavailable."""
    if not is_complete(run):
        return False
    try:
        for artifact in run.artifacts.all():
            preview.snapshot(
                settings.EXPORT_DIR,
                artifact.relative_path,
                maximum=artifact.byte_size,
                sha256=artifact.sha256,
                size=artifact.byte_size,
            )
    except (OSError, ValueError):
        return False
    return True


def run(context):
    context.checkpoint()
    snapshot, pins = load_pinned_inputs(context.payload["snapshot_id"], checkpoint=context.checkpoint)
    if snapshot.run.job_id != context.job_id or snapshot.kind != "FULL" or snapshot.sha256 != context.payload["sha256"]:
        raise ValidationError("Unsupported or foreign generation authorization")
    deadline = time.monotonic() + MAX_RUN_SECONDS

    def guard():
        if time.monotonic() > deadline:
            raise ValidationError("Generation time limit exceeded")
        context.checkpoint()

    with ExitStack() as stack:
        root, data_root = _roots(stack)
        processor = _processor(data_root, guard)
        prune(data_root, ".staging/generation")
        total = 0
        for index, person in enumerate(snapshot.payload["participants"]):
            context.checkpoint(min(90, index * 90 // len(snapshot.payload["participants"])))
            publication = _plan(context, snapshot, person)
            artifact = _existing(publication, root, guard)
            if not artifact:
                if total >= MAX_RUN_BYTES:
                    raise ValidationError("Generation output limit exceeded")
                processor.limits = replace(processor.limits, max_output_bytes=min(104_857_600, MAX_RUN_BYTES - total))
                _cleanup(context, publication, root)
                _compose(context, snapshot, pins, person, processor, publication, root)
                artifact = _existing(publication, root, guard)
            total += artifact.byte_size
            if total > MAX_RUN_BYTES:
                raise ValidationError("Generation output limit exceeded")
        final = inventory(snapshot.run)
        for publication in snapshot.run.publications.all():
            _existing(publication, root, guard)
        guard()
        context.commit_metadata(
            lambda: ExportCompletion.objects.get_or_create(
                run=snapshot.run, defaults={"inventory": final, "sha256": fingerprint(final)}
            )
        )


def _publication(context, intent):
    if set(intent.payload) != {"publication"}:
        raise ValidationError("Invalid publication identity")
    publication = ExportPublication.objects.select_related("run__snapshot").get(
        pk=intent.payload["publication"], run__job_id=context.job_id
    )
    if intent.key != "artifact:" + publication.participant_id.hex:
        raise ValidationError("Invalid participant publication key")
    return publication, publication.stages.get(attempt=intent.attempt)


def acknowledge(context, intent):
    publication, stage = _publication(context, intent)
    if intent.result != stage.receipt:
        raise ValidationError("Invalid output receipt")
    artifact, _ = ExportArtifact.objects.get_or_create(
        run=publication.run,
        participant_id=publication.participant_id,
        defaults={
            "relative_path": publication.relative_path,
            "sha256": stage.sha256,
            "byte_size": stage.byte_size,
            "manifest": stage.manifest,
            "intent": intent,
        },
    )
    artifact.full_clean()


def reconcile(context, intent):
    publication, stage = _publication(context, intent)
    with ExitStack() as stack:
        root, data_root = _roots(stack)
        if not root.exists(publication.relative_path):
            return "ABANDONED", {}
        files.verify_published(
            root,
            publication.relative_path,
            sha256=stage.sha256,
            size=stage.byte_size,
            staged_path=stage.relative_path,
            processor=_processor(data_root, context.checkpoint),
            checkpoint=context.checkpoint,
            durable=True,
        )
    return "APPLIED", stage.receipt


def recover_cleanup(context):
    """Dead-owner only; preserve uncertain linked evidence, prune owned scratch."""
    from apps.jobs.models import OperationIntent

    with ExitStack() as stack:
        root, data_root = _roots(stack)
        _processor(data_root, context.checkpoint)
        prune(data_root, ".staging/generation")
        for publication in ExportPublication.objects.filter(run__job_id=context.job_id):
            intents = OperationIntent.objects.filter(
                job_id=context.job_id, key="artifact:" + publication.participant_id.hex
            )
            intent = intents.first()
            if intent and intent.state in {"PENDING", "REVIEW_REQUIRED"}:
                continue
            if intent and intent.state == "APPLIED":
                _existing(publication, root, context.checkpoint)
            for number in range(1, context.attempt_number + 1):
                path = f".staging/{publication.pk.hex}/attempt-{number}.pdf"
                if root.exists(path):
                    info = root.metadata(path)
                    if info.st_uid != os.geteuid():
                        raise files.FileError("UNSAFE_STAGING")
                    files.discard_stage(root, path, files.identity(info))


def register():
    queue.HANDLERS[Job.Kind.GENERATE] = queue.Handler(
        validate_job_payload,
        run,
        idempotent=True,
        max_attempts=3,
        reconcile=reconcile,
        acknowledge=acknowledge,
        recover_cleanup=recover_cleanup,
    )
