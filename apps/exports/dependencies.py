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
    if session.include_content:
        editions = bounded(archive.ContentEdition.objects.filter(arrangement_id__in=arrangements), 10_000)
        revisions = bounded(archive.ContentEditionRevision.objects.filter(edition_id__in=[e.pk for e in editions]))
        references = bounded(archive.ContentReference.objects.filter(revision_id__in=[r.pk for r in revisions]))
        logical = bounded(
            archive.LogicalPageRevision.objects.filter(pk__in=[r.logical_page_revision_id for r in references])
        )
        logical_history = bounded(
            archive.LogicalPageRevision.objects.filter(logical_page_id__in=[r.logical_page_id for r in logical])
        )
        regions = bounded(
            archive.PageRegionRevision.objects.filter(
                pk__in=[r.region_revision_id for r in logical if r.region_revision_id]
            )
        )
        region_history = bounded(
            archive.PageRegionRevision.objects.filter(region_id__in=[r.region_id for r in regions])
        )
        content_files = bounded(archive.ArchiveFile.objects.filter(pk__in=[r.archive_file_id for r in references]))
        operations = bounded(
            archive.FileOperation.objects.filter(pk__in=[f.publication_operation_id for f in content_files])
        )
        payload["content"] = {
            "editions": rows(editions),
            "revisions": rows(revisions),
            "references": rows(references),
            "logical_revisions": rows(logical_history),
            "region_revisions": rows(region_history),
            "inspections": rows(
                bounded(archive.ContentInspection.objects.filter(revision_id__in=[r.pk for r in revisions]))
            ),
            "confirmations": rows(
                bounded(
                    archive.ContentConfirmation.objects.filter(inspection__revision_id__in=[r.pk for r in revisions])
                )
            ),
            "files": rows(content_files),
            "versions": rows(
                bounded(archive.SourceVersion.objects.filter(pk__in=[f.source_version_id for f in content_files]))
            ),
            "source_files": rows(
                bounded(
                    archive.SourceFile.objects.filter(
                        versions__pk__in=[f.source_version_id for f in content_files]
                    ).distinct()
                )
            ),
            "operations": rows(operations),
            "intents": rows([operation.intent for operation in operations]),
            "source_pages": rows(
                bounded(
                    archive.SourcePage.objects.filter(
                        Q(pk__in=[r.source_page_id for r in logical if r.source_page_id])
                        | Q(regions__revisions__pk__in=[r.pk for r in regions])
                    ).distinct()
                )
            ),
        }
    return json.loads(json.dumps(payload, cls=DjangoJSONEncoder))
