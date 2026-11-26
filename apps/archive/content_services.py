"""Explicit ordered proposals and revision-bound visual confirmation.

No filesystem publication, inferred approval, or mutation of legacy assignments.
"""

from uuid import UUID, uuid4

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F

from apps.archive import models as m
from apps.archive.content_manifest import manifest_fingerprint
from apps.archive.library_services import verify_publication
from apps.archive.services import ArchiveConflict, _actor
from apps.catalog.models import Arrangement


def _lock_edition(edition_id, using):
    arrangements = m.ContentEdition.objects.using(using).filter(pk=edition_id).values("arrangement_id")
    if not Arrangement.objects.using(using).filter(pk__in=arrangements).update(revision=F("revision")):
        raise ValidationError("Content edition does not exist.")
    return m.ContentEdition.objects.using(using).get(pk=edition_id)


def _latest(revision, using):
    if revision.edition.revisions.using(using).order_by("-number").values_list("pk", flat=True).first() != revision.pk:
        raise ArchiveConflict()
    references = list(
        revision.references.using(using).select_related("logical_page_revision__logical_page", "archive_file")
    )
    if len(references) != len(revision.manifest):
        raise ValidationError("Content proposal is incomplete.")
    if manifest_fingerprint(revision.manifest) != revision.fingerprint:
        raise ValidationError("Content proposal fingerprint changed.")
    for ref in references:
        # Revalidate even when rows were created through bulk or recovery paths.
        ref.validate_input()
        logical = ref.logical_page_revision
        if (
            logical.logical_page.revisions.using(using).order_by("-number").values_list("pk", flat=True).first()
            != logical.pk
        ):
            raise ArchiveConflict()
        if logical.region_revision_id:
            region = logical.region_revision
            if (
                region.region.revisions.using(using).order_by("-number").values_list("pk", flat=True).first()
                != region.pk
            ):
                raise ArchiveConflict()
        file = ref.archive_file
        if (
            file.revision != ref.file_revision
            or file.publication_state != "AVAILABLE"
            or file.review_state in ("REJECTED", "WITHDRAWN")
        ):
            raise ArchiveConflict()
    return references


def propose_content(edition_id, *, expected_number, inputs, using="default"):
    """Inputs are explicit (logical revision UUID, BASE publication UUID) pairs."""
    inputs = list(inputs)
    if not 1 <= len(inputs) <= 1000:
        raise ValidationError("Content proposals require one to 1000 occurrences.")
    try:
        inputs = [(UUID(str(logical)), UUID(str(file))) for logical, file in inputs]
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValidationError("Content inputs require explicit UUID pairs.") from exc
    with transaction.atomic(using=using):
        edition = _lock_edition(edition_id, using)
        current = edition.revisions.order_by("-number").values_list("number", flat=True).first() or 0
        if expected_number != current:
            raise ArchiveConflict()
        files = m.ArchiveFile.objects.using(using).in_bulk([item[1] for item in inputs])
        manifest = []
        for logical_id, file_id in inputs:
            file = files.get(file_id)
            if file is None:
                raise ValidationError("Content publication does not exist.")
            manifest.append(
                {
                    "occurrence_id": str(uuid4()),
                    "logical_page_revision_id": str(logical_id),
                    "archive_file_id": str(file.pk),
                    "file_revision": file.revision,
                }
            )
        revision = m.ContentEditionRevision.objects.using(using).create(
            edition=edition, number=current + 1, manifest=manifest, fingerprint=manifest_fingerprint(manifest)
        )
        for sequence, item in enumerate(manifest):
            m.ContentReference.objects.using(using).create(
                id=item["occurrence_id"],
                revision=revision,
                sequence=sequence,
                logical_page_revision_id=item["logical_page_revision_id"],
                archive_file_id=item["archive_file_id"],
                file_revision=item["file_revision"],
            )
        _latest(revision, using)
        return revision


def inspect_content(revision_id, *, actor, expected_fingerprint, visually_reviewed, using="default"):
    """Caller presents exact source context and all occurrences before attestation."""
    initial = m.ContentEditionRevision.objects.using(using).get(pk=revision_id)
    for ref in _latest(initial, using):
        if not verify_publication(ref.archive_file):
            raise ValidationError("Content input failed integrity verification.")
    with transaction.atomic(using=using):
        _lock_edition(initial.edition_id, using)
        revision = m.ContentEditionRevision.objects.using(using).get(pk=revision_id)
        _latest(revision, using)
        if expected_fingerprint != revision.fingerprint:
            raise ArchiveConflict()
        return m.ContentInspection.objects.using(using).create(
            revision=revision,
            reviewer=_actor(actor, using),
            fingerprint=expected_fingerprint,
            visually_reviewed=visually_reviewed,
        )


def confirm_content(inspection_id, *, actor, using="default"):
    initial = m.ContentInspection.objects.using(using).select_related("revision").get(pk=inspection_id)
    for ref in _latest(initial.revision, using):
        if not verify_publication(ref.archive_file):
            raise ValidationError("Content input failed integrity verification.")
    with transaction.atomic(using=using):
        _lock_edition(initial.revision.edition_id, using)
        inspection = m.ContentInspection.objects.using(using).select_related("revision").get(pk=inspection_id)
        _latest(inspection.revision, using)
        confirmation, _ = m.ContentConfirmation.objects.using(using).get_or_create(
            inspection=inspection, defaults={"actor": _actor(actor, using)}
        )
        if confirmation.actor_id != _actor(actor, using).pk:
            raise ValidationError("Only the inspecting reviewer can confirm content.")
        return confirmation
