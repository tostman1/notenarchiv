"""Ordered immutable musical inputs, including unchanged whole-file editions.

This adapter does not create confirmations, rewrite legacy IDs or modify snapshots.
Derivatives deliberately remain whole-file inputs: source-page metadata describes
the original PDF, not the processed artifact.
"""

from dataclasses import dataclass
from uuid import UUID, uuid5

from django.core.exceptions import ValidationError

from apps.archive import models as m

OCCURRENCE_NAMESPACE = UUID("77c91ccb-4a63-468a-898b-91a1ddbca24c")


@dataclass(frozen=True)
class ContentInput:
    occurrence_id: UUID
    sequence: int
    file_id: UUID
    file_revision: int
    source_version_id: UUID
    sha256: str
    byte_size: int
    root_kind: str
    relative_path: str
    source_page_id: UUID | None = None
    page_index: int | None = None
    logical_page_revision_id: UUID | None = None
    bounds_points: tuple[float, float, float, float] | None = None
    orientation: int = 0


@dataclass(frozen=True)
class ResolvedContentEdition:
    edition_id: UUID
    arrangement_id: UUID
    part_id: UUID
    inputs: tuple[ContentInput, ...]
    legacy_assignment_id: UUID | None = None


@dataclass(frozen=True)
class ContentResolution:
    status: str
    origin: str
    edition: ResolvedContentEdition | None = None


def resolve_legacy_content(arrangement_id, part_id, *, explicit_assignment_id=None, using="default"):
    """Use the existing shared selection rules, including explicit-choice failure.

    A separate eligibility recheck after selection fails closed on concurrent
    withdrawal. It must not turn an unavailable manual choice into a fallback.
    """
    from apps.archive.edition_services import resolve

    selected = resolve(arrangement_id, part_id, explicit_assignment_id=explicit_assignment_id, using=using)
    if selected.assignment is None:
        return ContentResolution(selected.status, selected.origin)
    try:
        edition = legacy_content_edition(selected.assignment.pk, using=using, verify=False)
    except ValidationError:
        return ContentResolution("UNAVAILABLE", selected.origin)
    return ContentResolution(selected.status, selected.origin, edition)


def legacy_content_edition(assignment_id, *, using="default", verify=True):
    """Adapt only currently usable assignments; never infer region approval.

    The existing assignment UUID is the edition UUID. Stable occurrence UUIDs
    describe page order without additive DB writes or a second approval history.
    Call outside a write transaction when byte verification is requested.
    """
    assignment = (
        m.ArchiveAssignment.objects.using(using)
        .usable()
        .select_related("archive_file__source_version", "archive_file__publication_operation__intent")
        .filter(pk=assignment_id)
        .first()
    )
    if assignment is None:
        raise ValidationError("A confirmed usable whole-file assignment is required.")
    file = assignment.archive_file
    if verify:
        from apps.archive.library_services import verify_file

        if not verify_file(file):
            raise ValidationError("Whole-file content input failed integrity verification.")
    common = {
        "file_id": file.pk,
        "file_revision": file.revision,
        "source_version_id": file.source_version_id,
        "sha256": file.sha256,
        "byte_size": file.byte_size,
        "root_kind": file.root_kind,
        "relative_path": file.relative_path,
    }
    if file.kind == "BASE":
        pages = list(file.source_version.pages.using(using).order_by("page_index"))
        if [page.page_index for page in pages] != list(range(len(file.source_version.page_info))):
            raise ValidationError("Whole-file source-page inventory requires reconciliation.")
        inputs = tuple(
            ContentInput(
                occurrence_id=uuid5(OCCURRENCE_NAMESPACE, f"{assignment.pk}:{page.page_index}"),
                sequence=page.page_index,
                source_page_id=page.pk,
                page_index=page.page_index,
                **common,
            )
            for page in pages
        )
    else:
        inputs = (
            ContentInput(occurrence_id=uuid5(OCCURRENCE_NAMESPACE, f"{assignment.pk}:whole"), sequence=0, **common),
        )
    return ResolvedContentEdition(
        edition_id=assignment.pk,
        arrangement_id=file.arrangement_id,
        part_id=assignment.part_id,
        inputs=inputs,
        legacy_assignment_id=assignment.pk,
    )


def confirmed_content_edition(edition_id, *, using="default", verify=True):
    """Uniform ordered inputs, pinned to a currently eligible inspected revision."""
    from apps.archive.content_services import _latest
    from apps.archive.library_services import verify_publication

    edition = (
        m.ContentEdition.objects.using(using).select_related("arrangement__work", "part__instrument").get(pk=edition_id)
    )
    if not all(
        (
            edition.arrangement.active,
            edition.arrangement.work.active,
            edition.part.active,
            edition.part.instrument.active,
        )
    ):
        raise ValidationError("Content catalog identities are inactive.")
    revision = edition.revisions.using(using).order_by("-number").first()
    if (
        revision is None
        or not m.ContentConfirmation.objects.using(using).filter(inspection__revision=revision).exists()
    ):
        raise ValidationError("The current content revision requires explicit confirmation.")
    inputs = []
    for ref in sorted(_latest(revision, using), key=lambda item: item.sequence):
        file = ref.archive_file
        if verify and not verify_publication(file):
            raise ValidationError("Content input failed integrity verification.")
        logical = ref.logical_page_revision
        page = logical.source_page if logical.source_page_id else logical.region_revision.region.source_page
        inputs.append(
            ContentInput(
                occurrence_id=ref.pk,
                sequence=ref.sequence,
                file_id=file.pk,
                file_revision=ref.file_revision,
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
        )
    # Eligibility recheck after external verification; no fallback to older revisions.
    _latest(revision, using)
    return ResolvedContentEdition(edition.pk, edition.arrangement_id, edition.part_id, tuple(inputs))
