"""Authenticated unified export history; read-only classification and explicit actions."""

from uuid import UUID

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST

from apps.exports import library_services
from apps.exports.generation import verified_complete
from apps.exports.models import ExportArtifact, GenerationRun


def selection(request):
    values = {}
    for field in ("project", "participant"):
        if request.GET.get(field):
            try:
                values[field] = UUID(request.GET[field])
            except ValueError:
                raise Http404 from None
    for field, choices in (
        ("variant", {"READING", "PRINT"}),
        ("kind", {"FULL", "EXCERPT", "CONTENTS", "ARCHIVE_NOTES"}),
    ):
        if request.GET.get(field):
            if request.GET[field] not in choices:
                raise Http404
            values[field] = request.GET[field]
    return values


@never_cache
@login_required
@require_GET
def library(request):
    values = selection(request)
    artifacts = ExportArtifact.objects.select_related("run__snapshot__project", "run__job", "participant").order_by(
        "-created_at", "pk"
    )
    runs = GenerationRun.objects.select_related("snapshot__project", "job").order_by("-created_at", "pk")
    if "project" in values:
        from apps.projects.models import Project

        get_object_or_404(Project, pk=values["project"])
        artifacts = artifacts.filter(run__snapshot__project_id=values["project"])
        runs = runs.filter(snapshot__project_id=values["project"])
    if "participant" in values:
        artifacts = artifacts.filter(participant_id=values["participant"])
        runs = runs.filter(snapshot__participants__participant_id=values["participant"]).distinct()
        if "project" in values:
            from apps.projects.models import ProjectParticipant

            if not ProjectParticipant.objects.filter(pk=values["participant"], project_id=values["project"]).exists():
                raise Http404
    if "kind" in values:
        artifacts = artifacts.filter(run__snapshot__kind=values["kind"])
        runs = runs.filter(snapshot__kind=values["kind"])
    if "variant" in values:
        artifacts = artifacts.filter(variant=values["variant"])
    page = Paginator(artifacts, 10).get_page(request.GET.get("page"))
    if "variant" in values:
        if values["variant"] == "PRINT":
            runs = runs.filter(snapshot__payload__output_variant="PRINT")
        else:
            runs = runs.exclude(snapshot__payload__output_variant="PRINT")
    run_page = Paginator(runs, 10).get_page(request.GET.get("run_page"))
    cache = {}
    for artifact in page:
        artifact.classification = library_services.classify(artifact, cache=cache)
    query = request.GET.copy()
    query.pop("page", None)
    from apps.projects.models import Project, ProjectParticipant

    projects = Project.objects.order_by("name")[:501]
    participants = (
        ProjectParticipant.objects.filter(project_id=values["project"]).order_by("display_name")[:501]
        if "project" in values
        else []
    )
    return render(
        request,
        "exports/library.html",
        {
            "page": page,
            "runs": run_page,
            "filters": query.urlencode(),
            "values": values,
            "projects": projects,
            "participants": participants,
        },
    )


@never_cache
@login_required
@require_GET
def regenerate(request, artifact_id):
    artifact = get_object_or_404(ExportArtifact.objects.select_related("run__snapshot"), pk=artifact_id)
    snapshot = artifact.run.snapshot
    if snapshot.kind == "ARCHIVE_NOTES":
        return redirect(
            reverse("archive_generated_export")
            + "?variant="
            + artifact.variant
            + "&"
            + "&".join("files=" + c["id"] for c in snapshot.payload["archive_files"])
        )
    if snapshot.kind == "CONTENTS":
        return redirect("project_contents_export", snapshot.project_id)
    route = "project_preflight" if snapshot.kind == "FULL" else "project_excerpt"
    query = "participants=" + str(artifact.participant_id)
    query += "&variant=" + artifact.variant
    if snapshot.kind == "EXCERPT":
        query += "&" + "&".join("positions=" + p["id"] for p in snapshot.payload["positions"])
    return redirect(reverse(route, args=[snapshot.project_id]) + "?" + query)


@never_cache
@login_required
@require_POST
def batch_download(request):
    identifiers = request.POST.getlist("artifacts")
    if not 1 <= len(identifiers) <= 20 or len(set(identifiers)) != len(identifiers):
        return HttpResponse(_("Höchstens 20 verschiedene vollständige PDFs auswählen."), status=400)
    try:
        ids = [UUID(v) for v in identifiers]
    except ValueError:
        raise Http404 from None
    selected = list(ExportArtifact.objects.filter(pk__in=ids).select_related("run__snapshot", "run__job"))
    import time

    from django.db.models import Sum

    run_ids = {a.run_id for a in selected}
    total = ExportArtifact.objects.filter(run_id__in=run_ids).aggregate(size=Sum("byte_size"))["size"] or 0
    if len(selected) != len(ids) or total > 512 * 1024**2:
        raise Http404
    checked = set()
    deadline = time.monotonic() + 60
    for artifact in selected:
        if artifact.run_id not in checked:
            if time.monotonic() > deadline or not verified_complete(artifact.run):
                raise Http404
            checked.add(artifact.run_id)
    from pathlib import Path

    from django.conf import settings

    from apps.archive.download_services import StagedDownload
    from core import downloads
    from core.locking import ProcessLock

    parent = Path(settings.DIAGNOSTIC_LOG_DIR).parent
    for root in (
        settings.SOURCE_DIR,
        settings.CURATED_DIR,
        settings.PROCESSED_DIR,
        settings.STATUS_DIR,
        settings.EXPORT_DIR,
    ):
        if parent.resolve().is_relative_to(Path(root).resolve()) or Path(root).resolve().is_relative_to(
            parent.resolve()
        ):
            raise Http404
    lock = ProcessLock(parent / "export-download.lock")
    try:
        lock.__enter__()
        inputs = [
            downloads.Input(Path(settings.EXPORT_DIR), a.relative_path, a.sha256, a.byte_size, f"note-{a.pk}.pdf")
            for a in selected
        ]
        stream = downloads.build(inputs, downloads.scratch_directory(parent), zipped=True)
    except (ValueError, OSError):
        lock.__exit__()
        raise Http404 from None
    response = FileResponse(
        StagedDownload(stream, lock), as_attachment=True, filename="Notenausgaben.zip", content_type="application/zip"
    )
    response["X-Content-Type-Options"] = "nosniff"
    response["Cross-Origin-Resource-Policy"] = "same-origin"
    response["Cache-Control"] = "private, no-store"
    return response
