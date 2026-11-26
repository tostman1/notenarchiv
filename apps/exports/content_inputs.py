"""Versioned content authorization inputs; historical reads never select a newer edition."""

from dataclasses import asdict
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F

from apps.archive.content_contract import ContentInput, ResolvedContentEdition, confirmed_content_edition
from apps.archive.content_manifest import manifest_fingerprint
from apps.archive.content_models import ContentConfirmation, ContentEdition, ContentEditionRevision
from apps.archive.content_services import _latest
from apps.archive.library_services import verify_publication
from apps.catalog.models import Arrangement

SCHEMA = "confirmed-content-inputs-v1"


def capture_content(edition_id, *, using="default"):
    """Verify outside the writer lock, then pin the exact confirmation and ordered inputs."""
    resolved = confirmed_content_edition(edition_id, using=using)
    with transaction.atomic(using=using):
        if (
            not Arrangement.objects.using(using)
            .filter(pk__in=ContentEdition.objects.using(using).filter(pk=edition_id).values("arrangement_id"))
            .update(revision=F("revision"))
        ):
            raise ValidationError("Content edition is unavailable.")
        current = confirmed_content_edition(edition_id, using=using, verify=False)
        if current != resolved:
            raise ValidationError("Content changed during authorization.")
        revision = ContentEditionRevision.objects.using(using).filter(edition_id=edition_id).order_by("-number").first()
        if revision is None:
            raise ValidationError("Content revision is unavailable.")
        _latest(revision, using)
        confirmation = ContentConfirmation.objects.using(using).filter(inspection__revision=revision).first()
        if confirmation is None:
            raise ValidationError("Exact content confirmation is required.")
        inputs = []
        for item in resolved.inputs:
            entry = asdict(item)
            for key, value in entry.items():
                if isinstance(value, UUID):
                    entry[key] = str(value)
                elif isinstance(value, tuple):
                    entry[key] = list(value)
            inputs.append(entry)
        return {
            "schema": SCHEMA,
            "edition_id": str(resolved.edition_id),
            "arrangement_id": str(resolved.arrangement_id),
            "part_id": str(resolved.part_id),
            "revision_id": str(revision.pk),
            "fingerprint": revision.fingerprint,
            "confirmation_id": str(confirmation.pk),
            "inputs": inputs,
        }


def load_content(payload, *, using="default", verify=True):
    """Validate historical relational evidence and bytes without latest-revision eligibility."""
    keys = {
        "schema",
        "edition_id",
        "arrangement_id",
        "part_id",
        "revision_id",
        "fingerprint",
        "confirmation_id",
        "inputs",
    }
    if not isinstance(payload, dict) or set(payload) != keys or payload["schema"] != SCHEMA:
        raise ValidationError("Invalid content input schema.")
    confirmation = (
        ContentConfirmation.objects.using(using)
        .select_related("inspection__revision__edition")
        .filter(pk=payload["confirmation_id"])
        .first()
    )
    if confirmation is None:
        raise ValidationError("Historical content confirmation is unavailable.")
    revision = confirmation.inspection.revision
    edition = revision.edition
    if (
        str(revision.pk) != payload["revision_id"]
        or revision.fingerprint != payload["fingerprint"]
        or confirmation.inspection.fingerprint != revision.fingerprint
        or confirmation.inspection.visually_reviewed is not True
        or confirmation.actor_id != confirmation.inspection.reviewer_id
        or manifest_fingerprint(revision.manifest) != revision.fingerprint
        or str(edition.pk) != payload["edition_id"]
        or str(edition.arrangement_id) != payload["arrangement_id"]
        or str(edition.part_id) != payload["part_id"]
    ):
        raise ValidationError("Historical content identity mismatch.")
    references = list(
        revision.references.select_related(
            "archive_file",
            "logical_page_revision__source_page",
            "logical_page_revision__region_revision__region__source_page",
        ).order_by("sequence")
    )
    if not isinstance(payload["inputs"], list) or not references or len(references) != len(payload["inputs"]):
        raise ValidationError("Historical content inventory mismatch.")
    inputs = []
    verified = set()
    for sequence, (reference, entry) in enumerate(zip(references, payload["inputs"], strict=True)):
        reference.validate_input()
        logical = reference.logical_page_revision
        page = logical.source_page if logical.source_page_id else logical.region_revision.region.source_page
        file = reference.archive_file
        item = ContentInput(
            occurrence_id=reference.pk,
            sequence=sequence,
            file_id=file.pk,
            file_revision=reference.file_revision,
            source_version_id=page.source_version_id,
            sha256=file.sha256,
            byte_size=file.byte_size,
            root_kind=file.root_kind,
            relative_path=file.relative_path,
            source_page_id=page.pk,
            page_index=page.page_index,
            logical_page_revision_id=logical.pk,
            bounds_points=tuple(logical.content_bounds_points),
            orientation=logical.orientation,
        )
        expected = asdict(item)
        expected = {
            key: str(value) if isinstance(value, UUID) else list(value) if isinstance(value, tuple) else value
            for key, value in expected.items()
        }
        if reference.sequence != sequence or entry != expected or file.revision != reference.file_revision:
            raise ValidationError("Historical ordered input mismatch.")
        if verify and file.pk not in verified:
            if not verify_publication(file):
                raise ValidationError("Historical publication integrity failed.")
            verified.add(file.pk)
        inputs.append(item)
    return ResolvedContentEdition(edition.pk, edition.arrangement_id, edition.part_id, tuple(inputs))
