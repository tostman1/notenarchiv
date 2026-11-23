"""Verified preflight authorization and atomic enqueue, with no mutable run inputs."""

from uuid import UUID

from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils.translation import gettext_lazy as _

from apps.archive.library_services import verify_file
from apps.exports.dependencies import dependency_payload
from apps.exports.models import GenerationRun, GenerationSnapshot, SnapshotInput, SnapshotParticipant, SnapshotPosition
from apps.jobs.models import Job
from apps.jobs.services import queue
from apps.projects.models import Project
from apps.projects.preflight_services import SALT, build_report, fingerprint, validate_acknowledgement
from apps.projects.resolution_services import ResolutionSession
from apps.projects.services import reviewer


def authorize(project_id, *, participant_ids, position_ids, token, acknowledgements, actor, kind="FULL"):
    if kind not in {"FULL", "EXCERPT"}:
        raise ValidationError(_("Nicht unterstützter Generierungstyp."))
    # Long hash/parser work runs before acquiring the SQLite writer lock.
    report = build_report(project_id, participant_ids=participant_ids, position_ids=position_ids)
    participant_ids = list(report.session.participants)
    position_ids = list(report.session.positions)
    validate_acknowledgement(report, token, acknowledgements, actor)
    request_id = signing.loads(token, salt=SALT, max_age=1800)["request_id"]
    with transaction.atomic():
        if not Project.objects.filter(pk=project_id, revision=report.session.project.revision, status="ACTIVE").update(
            revision=F("revision")
        ):
            raise ValidationError(_("Projekt geändert oder archiviert; erneut prüfen."))
        actor = reviewer(actor)
        existing = GenerationSnapshot.objects.filter(request_id=request_id).first()
        if existing:
            if (
                existing.actor_id != actor.pk
                or existing.preflight_sha256 != report.digest
                or existing.kind != kind
                or existing.acknowledgements != sorted(acknowledgements)
            ):
                raise ValidationError(_("Freigabe bereits anders verwendet; erneut prüfen."))
            return existing.run
        current = ResolutionSession(project_id, participant_ids=participant_ids, position_ids=position_ids)
        if dependency_payload(current) != report.payload["dependencies"]:
            raise ValidationError(_("Eingaben während der Freigabe geändert; erneut prüfen."))
        for row in report.rows:
            for cell in row["cells"]:
                result = cell["resolution"]
                if result.usable and current.resolve(result.position_id, result.participant_id) != result:
                    raise ValidationError(_("Effektive Zuordnung geändert; erneut prüfen."))
        if kind == "FULL" and set(current.positions) != set(
            current.project.positions.filter(active=True).values_list("pk", flat=True)
        ):
            raise ValidationError(
                _("Vollständige Mappen benötigen alle gemeinsamen Positionen einschließlich Reserven.")
            )
        snapshot = GenerationSnapshot.objects.create(
            request_id=request_id,
            project_id=project_id,
            project_revision=current.project.revision,
            kind=kind,
            payload=report.payload,
            sha256=fingerprint(report.payload),
            preflight_sha256=report.digest,
            actor=actor,
            acknowledgements=sorted(acknowledgements),
        )
        for person in current.participants.values():
            SnapshotParticipant.objects.create(
                snapshot=snapshot,
                participant=person,
                default_part_id=person.default_part_id,
                role_id=person.role_id,
                display_name=person.display_name,
            )
        for position in current.positions.values():
            SnapshotPosition.objects.create(
                snapshot=snapshot,
                position=position,
                arrangement_id=position.arrangement_id,
                number=position.order,
                title=str(position.arrangement) if position.arrangement_id else "Reserve",
            )
        for row in report.rows:
            for cell in row["cells"]:
                result = cell["resolution"]
                if result.usable:
                    SnapshotInput.objects.create(
                        snapshot=snapshot,
                        position_id=result.position_id,
                        participant_id=result.participant_id,
                        part_id=result.effective_part_id,
                        assignment_id=result.assignment_id,
                        archive_file_id=result.file_id,
                        source_version_id=result.source_version_id,
                        sha256=result.sha256,
                        byte_size=result.byte_size,
                        file_revision=result.file_revision,
                    )
        job = queue.enqueue(Job.Kind.GENERATE, {"snapshot_id": str(snapshot.pk), "sha256": snapshot.sha256})
        return GenerationRun.objects.create(snapshot=snapshot, job=job)


def validate_job_payload(payload):
    if set(payload) != {"snapshot_id", "sha256"}:
        raise ValueError("Authorized generation snapshot required")
    identifier = UUID(payload["snapshot_id"])
    snapshot = GenerationSnapshot.objects.filter(pk=identifier, sha256=payload["sha256"]).first()
    if snapshot is None or fingerprint(snapshot.payload) != snapshot.sha256:
        raise ValueError("Invalid generation authorization")
    return {"snapshot_id": str(identifier), "sha256": snapshot.sha256}


def load_pinned_inputs(snapshot_id, *, checkpoint=lambda: None):
    """Read exact immutable cells; never resolve current project defaults or preferences."""
    snapshot = GenerationSnapshot.objects.get(pk=snapshot_id)
    snapshot.full_clean()
    if fingerprint(snapshot.payload) != snapshot.sha256 or snapshot.preflight_sha256 != snapshot.sha256:
        raise ValidationError("Snapshot fingerprint mismatch")
    if {str(p.participant_id) for p in snapshot.participants.all()} != {
        p["id"] for p in snapshot.payload["participants"]
    }:
        raise ValidationError("Snapshot participant inventory mismatch")
    if {str(p.position_id) for p in snapshot.positions.all()} != {p["id"] for p in snapshot.payload["positions"]}:
        raise ValidationError("Snapshot position inventory mismatch")
    pins = list(
        snapshot.inputs.select_related("assignment", "archive_file__publication_operation__intent", "source_version")
    )
    expected = {
        (cell["position_id"], cell["participant_id"]): cell
        for cell in snapshot.payload["cells"]
        if cell["status"] in {"AVAILABLE", "SUBSTITUTED"}
    }
    if len(expected) != len(pins):
        raise ValidationError("Snapshot pin inventory mismatch")
    verified = set()
    for pin in pins:
        checkpoint()
        cell = expected.get((str(pin.position_id), str(pin.participant_id)))
        file = pin.archive_file
        if (
            cell is None
            or any(
                str(getattr(pin, field)) != str(cell[key])
                for field, key in (
                    ("assignment_id", "assignment_id"),
                    ("archive_file_id", "file_id"),
                    ("part_id", "effective_part_id"),
                    ("source_version_id", "source_version_id"),
                    ("sha256", "sha256"),
                    ("byte_size", "byte_size"),
                    ("file_revision", "file_revision"),
                )
            )
            or file.review_state != "CONFIRMED"
            or file.publication_state != "AVAILABLE"
            or file.revision != pin.file_revision
            or file.sha256 != pin.sha256
            or file.byte_size != pin.byte_size
            or file.source_version_id != pin.source_version_id
            or file.root_kind != cell["root_kind"]
            or file.relative_path != cell["relative_path"]
        ):
            raise ValidationError("Pinned input changed or unavailable")
        if (
            pin.assignment.state != "CONFIRMED"
            or pin.assignment.part_id != pin.part_id
            or pin.assignment.archive_file_id != file.pk
        ):
            raise ValidationError("Pinned source verification failed")
        if file.pk not in verified:
            if not verify_file(file):
                raise ValidationError("Pinned source verification failed")
            verified.add(file.pk)
    return snapshot, pins


def run_authorized(context):
    context.checkpoint()
    snapshot, _pins = load_pinned_inputs(context.payload["snapshot_id"], checkpoint=context.checkpoint)
    if snapshot.run.job_id != context.job_id:
        raise ValidationError("Job is not bound to snapshot authorization")
    # WP-36b installs authorization, not a fake successful PDF handler. WP-37b
    # supplies the real renderer/publication contract; premature jobs fail closed.
    raise ValidationError("PDF generation handler not yet available")


def register():
    queue.HANDLERS[Job.Kind.GENERATE] = queue.Handler(validate_job_payload, run_authorized)
