"""Canonical DB-only recheck: never hold a write transaction over PDF I/O."""

import json

from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Q

from apps.archive import library_services
from apps.archive import models as archive
from apps.projects.resolution_services import bounded


def rows(values):
    return sorted(
        ({field.attname: getattr(row, field.attname) for field in row._meta.concrete_fields} for row in values),
        key=lambda row: str(row.get("id")),
    )


def dependency_payload(session):
    arrangements = {p.arrangement_id for p in session.positions.values() if p.arrangement_id}
    files = {a.archive_file.pk: a.archive_file for a in session.assignments.values()}
    payload = {
        "project": rows([session.project]),
        "positions": rows(session.positions.values()),
        "arrangements": rows(
            {p.arrangement.pk: p.arrangement for p in session.positions.values() if p.arrangement_id}.values()
        ),
        "works": rows(
            {p.arrangement.work.pk: p.arrangement.work for p in session.positions.values() if p.arrangement_id}.values()
        ),
        "participants": rows(session.participants.values()),
        "parts": rows(session.parts.values()),
        "instruments": rows({part.instrument.pk: part.instrument for part in session.parts.values()}.values()),
        "roles": rows(
            {person.role.pk: person.role for person in session.participants.values() if person.role_id}.values()
        ),
        "overrides": rows(session.overrides.values()),
        "mappings": rows(session.mappings),
        "local_rules": rows(session.local_rules),
        "global_rules": rows(session.global_rules),
        "global_revision": session.global_revision,
        "project_preferences": rows(session.project_preferences.values()),
        "position_preferences": rows(session.position_preferences.values()),
        "archive_preferences": rows(session.archive_preferences.values()),
        "assignments": rows(session.assignments.values()),
        "files": rows({a.archive_file.pk: a.archive_file for a in session.assignments.values()}.values()),
        "versions": rows(
            {
                a.archive_file.source_version.pk: a.archive_file.source_version for a in session.assignments.values()
            }.values()
        ),
        "source_files": rows(
            {f.source_version.source_file.pk: f.source_version.source_file for f in files.values()}.values()
        ),
        "operations": rows({f.publication_operation.pk: f.publication_operation for f in files.values()}.values()),
        "intents": rows(
            {f.publication_operation.intent.pk: f.publication_operation.intent for f in files.values()}.values()
        ),
        "proposals": rows(
            bounded(archive.ArchiveProposal.objects.filter(pk__in={f.approved_proposal_id for f in files.values()}))
        ),
        "pending": rows(
            bounded(
                library_services.pending_files()
                .filter(
                    Q(current_proposal__arrangement_id__in=arrangements)
                    | Q(current_proposal__isnull=True, candidates__proposed_arrangement_id__in=arrangements)
                )
                .distinct(),
                2000,
            )
        ),
        "unavailable": rows(
            bounded(
                archive.ArchiveFile.objects.filter(
                    arrangement_id__in=arrangements,
                    review_state="CONFIRMED",
                    publication_state__in=["MISSING", "CORRUPT"],
                ),
                2000,
            )
        ),
    }
    return json.loads(json.dumps(payload, cls=DjangoJSONEncoder))
