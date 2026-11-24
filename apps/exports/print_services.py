"""Explicit actor-bound print authorization preserves exact previous reading inputs."""

import copy
from uuid import UUID, uuid4

from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from apps.exports.models import GenerationRun, GenerationSnapshot, SnapshotInput, SnapshotParticipant, SnapshotPosition
from apps.exports.snapshot_services import load_pinned_inputs
from apps.jobs.services import queue
from apps.projects.preflight_services import fingerprint
from apps.projects.services import reviewer

SALT = "exports.print.v1"


def token(snapshot, actor):
    return signing.dumps(
        {"source": str(snapshot.pk), "sha256": snapshot.sha256, "actor": str(actor.pk), "request": str(uuid4())},
        salt=SALT,
    )


def authorize_print(snapshot_id, authorization, actor):
    actor = reviewer(actor)
    try:
        value = signing.loads(authorization, salt=SALT, max_age=1800)
    except signing.BadSignature:
        raise ValidationError(_("Druckfreigabe abgelaufen oder ungültig.")) from None
    snapshot, _pins = load_pinned_inputs(snapshot_id)
    from apps.exports.generation import verified_complete

    if (
        value.get("source") != str(snapshot.pk)
        or value.get("sha256") != snapshot.sha256
        or value.get("actor") != str(actor.pk)
        or snapshot.payload["options"]["layout"] != "REGULAR"
        or snapshot.payload.get("output_variant") == "PRINT"
        or not verified_complete(snapshot.run)
    ):
        raise ValidationError(_("Druckfreigabe passt nicht zu den festen Eingaben; erneut prüfen."))
    try:
        UUID(value["request"])
    except (KeyError, ValueError, TypeError):
        raise ValidationError(_("Ungültige Druckfreigabe.")) from None
    payload = copy.deepcopy(snapshot.payload)
    payload["output_variant"] = "PRINT"
    with transaction.atomic():
        from django.db.models import F

        if snapshot.project_id:
            from apps.projects.models import Project

            Project.objects.filter(pk=snapshot.project_id).update(revision=F("revision"))
        else:
            from apps.archive.models import ArchiveFile

            ArchiveFile.objects.filter(pk=_pins[0].archive_file_id).update(revision=F("revision"))
        existing = GenerationSnapshot.objects.filter(request_id=value["request"]).first()
        if existing:
            if existing.source_snapshot_id != snapshot.pk or existing.actor_id != actor.pk:
                raise ValidationError(_("Druckfreigabe bereits anders verwendet."))
            return existing.run
        target = GenerationSnapshot.objects.create(
            request_id=value["request"],
            project_id=snapshot.project_id,
            project_revision=snapshot.project_revision,
            kind=snapshot.kind,
            payload=payload,
            sha256=fingerprint(payload),
            preflight_sha256=fingerprint(payload),
            actor=actor,
            acknowledgements=snapshot.acknowledgements,
            source_snapshot=snapshot,
        )
        for model, related in (
            (SnapshotParticipant, "participants"),
            (SnapshotPosition, "positions"),
            (SnapshotInput, "inputs"),
        ):
            for pin in getattr(snapshot, related).all():
                fields = {
                    f.attname: getattr(pin, f.attname)
                    for f in pin._meta.fields
                    if f.name not in {"id", "created_at", "snapshot"}
                }
                model.objects.create(snapshot=target, **fields)
        job = queue.enqueue("GENERATE", {"snapshot_id": str(target.pk), "sha256": target.sha256})
        return GenerationRun.objects.create(snapshot=target, job=job)
