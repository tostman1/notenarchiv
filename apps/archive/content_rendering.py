"""Verified content-to-derivative bridge; never publication or musical approval."""

from django.conf import settings
from django.core.exceptions import ValidationError

from apps.archive.content_contract import confirmed_content_edition, legacy_content_edition
from core import preview
from core.pdf import Selection


def render_content(edition_id, *, processor, legacy=False, using="default"):
    """Render only a currently eligible edition; recheck eligibility before returning.

    This read-only bridge does not replace generation authorization or immutable
    snapshot pins. Callers must supply those before exposing a product export.
    """
    adapter = legacy_content_edition if legacy else confirmed_content_edition
    edition = adapter(edition_id, using=using)
    maximum = settings.PDF_MAX_BYTES
    unique, sources, total = {}, [], 0
    for item in edition.inputs:
        if item.file_id in unique:
            continue
        total += item.byte_size
        if total > maximum or len(sources) >= 16:
            raise ValidationError("Content rendering exceeds the supported input bound.")
        root = {"CLEAN": settings.CURATED_DIR, "PROCESSED": settings.PROCESSED_DIR}.get(item.root_kind)
        if root is None:
            raise ValidationError("Content rendering requires a published archive input.")
        data = preview.snapshot(root, item.relative_path, maximum=maximum, sha256=item.sha256, size=item.byte_size)
        unique[item.file_id] = len(sources)
        sources.append(data)
    worker = processor
    if legacy:
        # The legacy adapter's whole-document contract includes processed editions;
        # do not manufacture original source-page identities for their derivatives.
        output = worker.merge(tuple(Selection(data) for data in sources))
    else:
        selections = [
            {
                "input": unique[item.file_id],
                "page": item.page_index,
                "bounds": list(item.bounds_points),
                "orientation": item.orientation,
            }
            for item in edition.inputs
        ]
        output = worker.logical_pages(sources, selections)
    if adapter(edition_id, using=using) != edition:
        raise ValidationError("Content eligibility changed while rendering.")
    return output
