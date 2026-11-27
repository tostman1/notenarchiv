"""Explicit authorization of confirmed musical sequences, not entire source files."""

from itertools import islice
from uuid import UUID, uuid4

from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils.translation import gettext_lazy as _

from apps.archive.content_contract import confirmed_content_edition
from apps.archive.models import ContentEdition
from apps.catalog.models import Arrangement
from apps.exports.content_inputs import capture_content, load_content
from apps.exports.models import GenerationRun, GenerationSnapshot, SnapshotContentInput
from apps.jobs.services import queue
from apps.projects.preflight_services import fingerprint
from apps.projects.services import reviewer

SALT = "exports.content-generation.v1"
MAX_CONTENT_EDITIONS = 125


def report(identifiers):
    identifiers = list(islice(identifiers, MAX_CONTENT_EDITIONS + 1))
    if not 1 <= len(identifiers) <= MAX_CONTENT_EDITIONS:
        raise ValidationError(_("Eine bis 125 bestätigte Inhaltsausgaben auswählen."))
    try:
        identifiers = [UUID(str(value)) for value in identifiers]
    except (ValueError, TypeError):
        raise ValidationError(_("Ungültige Inhaltsauswahl.")) from None
    if len(set(identifiers)) != len(identifiers):
        raise ValidationError(_("Inhaltsausgaben nicht mehrfach auswählen."))
    entries, files = [], {}
    for identifier in identifiers:
        captured = capture_content(identifier)
        title = str(ContentEdition.objects.select_related("arrangement__work").get(pk=identifier).arrangement)
        entries.append({"title": title, "content": captured})
        for item in captured["inputs"]:
            files[item["file_id"]] = item["byte_size"]
    if len(files) > 16 or sum(files.values()) > 104_857_600:
        raise ValidationError(_("Inhaltsauswahl überschreitet die Verarbeitungsgrenze."))
    return entries


def token(entries, actor, variant="READING"):
    actor = reviewer(actor)
    if variant not in {"READING", "PRINT"}:
        raise ValidationError(_("Ungültige Ausgabeart."))
    return signing.dumps(
        {"digest": fingerprint(entries), "actor": str(actor.pk), "request": str(uuid4()), "variant": variant},
        salt=SALT,
        compress=True,
    )


def authorize(identifiers, authorization, actor, variant="READING"):
    actor = reviewer(actor)
    try:
        value = signing.loads(authorization, salt=SALT, max_age=1800)
        request_id = UUID(value["request"])
    except (signing.BadSignature, KeyError, ValueError, TypeError):
        raise ValidationError(_("Inhaltsfreigabe abgelaufen oder ungültig.")) from None
    entries = report(identifiers)
    if (
        value.get("digest") != fingerprint(entries)
        or value.get("actor") != str(actor.pk)
        or variant not in {"READING", "PRINT"}
        or value.get("variant") != variant
    ):
        raise ValidationError(_("Inhaltsauswahl geändert; erneut prüfen."))
    payload = {
        "schema": 2,
        "project": "None",
        "revision": 0,
        "project_name": "Einzelnoten",
        "blocking": 0,
        "positions": [],
        "participants": [],
        "cells": [],
        "dependencies": {},
        "content_editions": [entry["content"] for entry in entries],
        "content_titles": [entry["title"] for entry in entries],
        "output_variant": variant,
        "options": {"layout": "REGULAR", "cover_enabled": False, "cover_title": "", "width_mm": 210, "height_mm": 297},
    }
    with transaction.atomic():
        Arrangement.objects.filter(pk=entries[0]["content"]["arrangement_id"]).update(revision=F("revision"))
        actor = reviewer(actor)
        # Metadata recheck under the SQLite writer lock; no parser/hash work here.
        for entry in entries:
            current = confirmed_content_edition(entry["content"]["edition_id"], verify=False)
            title = str(
                ContentEdition.objects.select_related("arrangement__work")
                .get(pk=entry["content"]["edition_id"])
                .arrangement
            )
            if current != load_content(entry["content"], verify=False) or title != entry["title"]:
                raise ValidationError(_("Inhalte während der Freigabe geändert."))
        existing = GenerationSnapshot.objects.filter(request_id=request_id).first()
        if existing:
            if existing.actor_id != actor.pk or existing.sha256 != fingerprint(payload):
                raise ValidationError(_("Freigabe bereits anders verwendet."))
            return existing.run
        snapshot = GenerationSnapshot.objects.create(
            request_id=request_id,
            project_revision=0,
            kind="ARCHIVE_NOTES",
            actor=actor,
            payload=payload,
            sha256=fingerprint(payload),
            preflight_sha256=fingerprint(payload),
        )
        for ordinal, captured in enumerate(payload["content_editions"]):
            SnapshotContentInput.objects.create(
                snapshot=snapshot,
                ordinal=ordinal,
                confirmation_id=captured["confirmation_id"],
                payload=captured,
            )
        job = queue.enqueue("GENERATE", {"snapshot_id": str(snapshot.pk), "sha256": snapshot.sha256})
        return GenerationRun.objects.create(snapshot=snapshot, job=job)
