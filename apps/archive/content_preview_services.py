"""Read-only inspection preview pinned to a saved region-content manifest."""

from django.http import Http404

from apps.archive import models as m
from apps.archive.content_manifest import manifest_fingerprint
from apps.archive.preview_services import region_sequence


def proposal_context(file, revision_id):
    """Validate the persisted single-publication region manifest without rendering."""
    if file.kind != "BASE":
        raise Http404
    revision = m.ContentEditionRevision.objects.filter(pk=revision_id).first()
    if revision is None or revision.fingerprint != manifest_fingerprint(revision.manifest):
        raise Http404
    references = list(
        revision.references.select_related("logical_page_revision__region_revision").order_by("sequence")[:17]
    )
    if not 1 <= len(references) <= 16 or len(references) != len(revision.manifest):
        raise Http404
    identifiers = []
    for reference in references:
        reference.validate_input()
        logical = reference.logical_page_revision
        if (
            reference.archive_file_id != file.pk
            or reference.file_revision != file.revision
            or not logical.region_revision_id
            or logical.orientation != 0
            or logical.content_bounds_points != logical.region_revision.bounds_points
        ):
            raise Http404
        identifiers.append(logical.region_revision_id)
    return revision, identifiers


def proposal_preview(file, revision_id):
    """Render the stored occurrence order, never a newly submitted selection."""
    _, identifiers = proposal_context(file, revision_id)
    return region_sequence(file, identifiers)
