"""Authenticated complete-run downloads, verified into private temporary bytes."""

from io import BytesIO

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST

from apps.exports import print_services
from apps.exports.generation import verified_complete
from apps.exports.models import ExportArtifact, GenerationRun
from core import preview


@never_cache
@login_required
@require_GET
def detail(request, run_id):
    run = get_object_or_404(GenerationRun.objects.select_related("job", "snapshot"), pk=run_id)
    complete = verified_complete(run)
    return render(
        request,
        "exports/detail.html",
        {
            "run": run,
            "complete": complete,
            "participants": run.snapshot.payload["participants"],
            "artifacts": list(run.artifacts.all()) if complete else [],
            "job_status": run.job.get_status_display(),
            "library_url": "/exports/"
            + ("?project=" + str(run.snapshot.project_id) if run.snapshot.project_id else "?kind=ARCHIVE_NOTES"),
            "print_token": print_services.token(run.snapshot, request.user)
            if complete
            and run.snapshot.payload.get("output_variant") != "PRINT"
            and run.snapshot.payload["options"]["layout"] == "REGULAR"
            else None,
        },
    )


@never_cache
@login_required
@require_GET
def download(request, artifact_id):
    artifact = get_object_or_404(ExportArtifact.objects.select_related("run__job", "run__snapshot"), pk=artifact_id)
    run = artifact.run
    if request.GET.get("project") and str(run.snapshot.project_id) != request.GET["project"]:
        raise Http404
    if not verified_complete(run):
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
    filename = (
        "Inhaltsverzeichnis.pdf"
        if run.snapshot.kind == "CONTENTS"
        else "Auszug.pdf"
        if run.snapshot.kind == "EXCERPT"
        else "Lese-PDF.pdf"
    )
    if artifact.variant == "PRINT":
        filename = "Druck-PDF.pdf"
    response = FileResponse(BytesIO(data), as_attachment=True, filename=filename, content_type="application/pdf")
    response["X-Content-Type-Options"] = "nosniff"
    response["Content-Security-Policy"] = "default-src 'none'; sandbox"
    response["Cross-Origin-Resource-Policy"] = "same-origin"
    return response


@never_cache
@login_required
@require_POST
def print_run(request, run_id):
    from django.core.exceptions import ValidationError
    from django.shortcuts import redirect

    run = get_object_or_404(GenerationRun.objects.select_related("snapshot"), pk=run_id)
    try:
        target = print_services.authorize_print(run.snapshot_id, request.POST.get("token", ""), request.user)
    except (ValidationError, ValueError, OSError):
        return HttpResponse(_("Druck-PDF nicht freigegeben; Eingaben erneut prüfen."), status=409)
    return redirect("generation_detail", target.pk)


@never_cache
@login_required
@require_GET
def viewer(request, artifact_id):
    artifact = get_object_or_404(ExportArtifact.objects.select_related("run__snapshot", "run__job"), pk=artifact_id)
    if not verified_complete(artifact.run):
        raise Http404
    from django.urls import reverse

    response = render(
        request,
        "exports/preview.html",
        {"artifact": artifact, "export_document_url": reverse("generation_download", args=[artifact.pk])},
    )
    response["Content-Security-Policy"] = (
        "default-src 'none'; script-src 'self'; worker-src 'self'; "
        "connect-src 'self'; style-src 'self'; img-src 'self' blob: data:; font-src 'self' blob:; "
        "object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
    )
    response["X-Content-Type-Options"] = "nosniff"
    response["Cross-Origin-Resource-Policy"] = "same-origin"
    response["Referrer-Policy"] = "same-origin"
    return response
