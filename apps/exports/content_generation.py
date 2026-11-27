"""Historical confirmed-input composition; never consult current preferences."""

from dataclasses import replace

from django.conf import settings
from django.core.exceptions import ValidationError

from apps.exports.content_export_services import MAX_CONTENT_EDITIONS
from apps.exports.content_inputs import load_content
from apps.exports.content_policy import plan
from core import preview


def load_pins(snapshot, checkpoint):
    pins = list(snapshot.content_inputs.order_by("ordinal"))
    entries = snapshot.payload.get("content_editions", [])
    titles = snapshot.payload.get("content_titles", [])
    if (
        not 1 <= len(entries) <= MAX_CONTENT_EDITIONS
        or len(pins) != len(entries)
        or len(titles) != len(entries)
        or snapshot.inputs.exists()
    ):
        raise ValidationError("Confirmed content pin inventory mismatch")
    for ordinal, (pin, entry) in enumerate(zip(pins, entries, strict=True)):
        checkpoint()
        if pin.ordinal != ordinal or pin.payload != entry or str(pin.confirmation_id) != entry["confirmation_id"]:
            raise ValidationError("Confirmed content pin identity mismatch")
        pin.full_clean()
        load_content(entry)
    return pins


def pieces(snapshot, pins, processor):
    editions = [load_content(pin.payload) for pin in pins]
    policy = snapshot.payload.get("shared_page_policy", "REGIONS")
    entries = [{"content": pin.payload} for pin in pins]
    consequences = plan(entries, policy)
    recorded = snapshot.payload.get("shared_page_plan")
    if recorded != consequences and not (policy == "REGIONS" and recorded is None):
        raise ValidationError("Shared-page consequence mismatch")
    if policy == "REGIONS":
        return render_editions(editions, snapshot.payload["content_titles"], processor)
    from apps.archive.library_services import verify_file
    from apps.archive.models import ArchiveFile, SourcePage

    transformed, titles = [], []
    for edition, title, decisions in zip(editions, snapshot.payload["content_titles"], consequences, strict=True):
        inputs = []
        for item, decision in zip(edition.inputs, decisions, strict=True):
            if not verify_file(ArchiveFile.objects.get(pk=item.file_id)):
                raise ValidationError("Whole-page source is not fully confirmed")
            if decision["emit"]:
                page = SourcePage.objects.get(pk=item.source_page_id)
                bounds = tuple(float(value) * page.user_unit for value in page.effective_crop_box)
                inputs.append(replace(item, bounds_points=bounds, orientation=0))
        if inputs:
            transformed.append(replace(edition, inputs=tuple(inputs)))
            titles.append(title)
    return render_editions(transformed, titles, processor)


def render_editions(editions, titles, processor):
    """Render exact historical ordered editions; titles and occurrence order are pinned."""
    if len(editions) != len(titles) or len(editions) > 1000:
        raise ValidationError("Confirmed content composition inventory mismatch")
    sources, indices, total = [], {}, 0
    for edition in editions:
        for item in edition.inputs:
            if item.file_id in indices:
                continue
            processor.checkpoint()
            total += item.byte_size
            if total > min(settings.PDF_MAX_BYTES, 104_857_600) or len(sources) >= 16:
                raise ValidationError("Confirmed content composition input bound exceeded")
            root = {"CLEAN": settings.CURATED_DIR, "PROCESSED": settings.PROCESSED_DIR}.get(item.root_kind)
            if root is None:
                raise ValidationError("Invalid confirmed content input root")
            data = preview.snapshot(
                root, item.relative_path, maximum=item.byte_size, sha256=item.sha256, size=item.byte_size
            )
            indices[item.file_id] = len(sources)
            sources.append(data)
    result, output_bytes = [], 0
    for ordinal, (edition, title) in enumerate(zip(editions, titles, strict=True)):
        selections = [
            {
                "input": indices[item.file_id],
                "page": item.page_index,
                "bounds": list(item.bounds_points),
                "orientation": item.orientation,
            }
            for item in edition.inputs
        ]
        data = processor.logical_pages(sources, selections)
        output_bytes += len(data)
        if output_bytes > min(settings.PDF_MAX_BYTES, 104_857_600):
            raise ValidationError("Confirmed content composition output bound exceeded")
        result.append({"number": ordinal + 1, "title": title, "state": "MUSIC", "data": data})
    return result
