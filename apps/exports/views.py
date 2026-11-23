"""Authenticated complete-run downloads, verified into private temporary bytes."""

from io import BytesIO

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from apps.exports.models import ExportArtifact, GenerationRun
from core import preview


@never_cache
@login_required
@require_GET
def detail(request, run_id):
    run = get_object_or_404(GenerationRun.objects.select_related("job", "snapshot"), pk=run_id)
    complete = run.job.status == "SUCCEEDED" and run.artifacts.count() == len(run.snapshot.payload["participants"])
    return render(request, "exports/detail.html", {"run": run, "complete": complete})


@never_cache
@login_required
@require_GET
def download(request, artifact_id):
    artifact = get_object_or_404(ExportArtifact.objects.select_related("run__job", "run__snapshot"), pk=artifact_id)
    run = artifact.run
    if run.job.status != "SUCCEEDED" or run.artifacts.count() != len(run.snapshot.payload["participants"]):
        raise Http404
    try:
        data = preview.snapshot(
            settings.EXPORT_DIR,
            artifact.relative_path,
            maximum=104_857_600,
            sha256=artifact.sha256,
            size=artifact.byte_size,
        )
    except (OSError, ValueError):
        raise Http404 from None
    response = FileResponse(BytesIO(data), as_attachment=True, filename="Lese-PDF.pdf", content_type="application/pdf")
    response["X-Content-Type-Options"] = "nosniff"
    return response
