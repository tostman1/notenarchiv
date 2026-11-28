"""Preview authorization/availability, separate from review and recognition."""

from pathlib import Path

from django.conf import settings
from django.http import Http404

from apps.archive.models import ArchiveAssignment, ArchiveFile
from core.locking import ProcessLock
from core.pdf.api import Processor
from core.pdf.types import Limits
from core.preview import snapshot


def preview_file(file_id, *, using="default"):
    derivative = (
        ArchiveFile.objects.using(using)
        .usable()
        .filter(
            pk=file_id,
            kind="DERIVATIVE",
            root_kind="PROCESSED",
            assignments__in=ArchiveAssignment.objects.using(using).usable(),
        )
        .select_related("source_version", "publication_operation__intent")
        .first()
    )
    if derivative is not None:
        from apps.archive.library_services import verify_file

        if not verify_file(derivative):
            raise Http404
        return derivative
    file = (
        ArchiveFile.objects.using(using)
        .select_related("source_version__source_file", "publication_operation__intent")
        .filter(
            pk=file_id,
            root_kind="CLEAN",
            kind="BASE",
            publication_state="AVAILABLE",
            source_version__pdf_state="VALID",
            publication_operation__state="APPLIED",
            publication_operation__intent__state="APPLIED",
            review_state__in=["PENDING", "APPROVAL_REQUESTED", "CONFIRMED"],
        )
        .first()
    )
    if file is None:
        raise Http404
    operation = file.publication_operation
    if (
        operation.archive_file_id != file.pk
        or operation.expected_receipt
        != {"root": file.root_kind, "path": file.relative_path, "sha256": file.sha256, "size": file.byte_size}
        or operation.intent.result != operation.expected_receipt
        or operation.intent.payload != operation.effect_payload
        or operation.intent.key != operation.effect_key
        or file.sha256 != file.source_version.sha256
        or file.byte_size != file.source_version.byte_size
    ):
        raise Http404
    return file


def preview_bytes(file):
    return snapshot(
        settings.CURATED_DIR if file.root_kind == "CLEAN" else settings.PROCESSED_DIR,
        file.relative_path,
        maximum=min(settings.PDF_MAX_BYTES, 104_857_600),
        sha256=file.sha256,
        size=file.byte_size,
    )


def thumbnail(file, page):
    if not 1 <= page <= min(len(file.source_version.page_info), 500):
        raise Http404
    # No persistent cache or unbounded scratch growth. A nonblocking shared OS
    # lock bounds native preview work to one request across web processes.
    root = Path(settings.DIAGNOSTIC_LOG_DIR).parent
    with ProcessLock(root / "preview-render.lock"):
        scratch = root / "preview-scratch"
        scratch.mkdir(mode=0o700, exist_ok=True)
        processor = Processor(
            scratch,
            limits=Limits(
                max_bytes=min(settings.PDF_MAX_BYTES, 104_857_600),
                max_pixels=min(settings.PDF_MAX_RENDER_PIXELS, 262_144),
                max_output_bytes=1_048_576,
                timeout_seconds=15,
                cpu_seconds=10,
            ),
        )
        return processor.thumbnail(preview_bytes(file), page=page - 1, max_edge=256)
