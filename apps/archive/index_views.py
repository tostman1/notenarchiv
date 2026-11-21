"""Authenticated indexing screens; all processing reuses durable backend jobs."""

from uuid import UUID

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST

from apps.archive import models as m
from apps.archive.index_forms import IndexSelection
from apps.archive.index_presentation import CANDIDATES, ERRORS, REVIEW, STATES, json_published, review_files
from apps.archive.indexing import queue_index
from apps.jobs.presentation import describe
from apps.jobs.services.queue import worker_is_healthy


@never_cache
@login_required
@require_GET
def overview(request):
    folders = m.SourceFolder.objects.annotate(
        pending_count=Count(
            "files__versions__archive_files",
            filter=Q(files__versions__archive_files__review_state__in=["PENDING", "REJECTED", "APPROVAL_REQUESTED"]),
            distinct=True,
        )
    ).order_by("relative_path")
    page = Paginator(folders, 25).get_page(request.GET.get("page"))
    for folder in page:
        folder.state_label = STATES[folder.index_state]
    scans = list(m.IndexScan.objects.select_related("job").order_by("-created_at")[:10])
    for scan in scans:
        describe(scan.job)
        scan.error_message = ERRORS.get(scan.error_code, _("Auftrag prüfen.")) if scan.error_code else ""
    return render(
        request,
        "archive/index.html",
        {
            "page": page,
            "scans": scans,
            "form": IndexSelection(),
            "pending_count": review_files().count(),
            "worker_available": worker_is_healthy(),
        },
    )


@never_cache
@login_required
@require_POST
def start(request):
    form = IndexSelection(request.POST)
    if form.is_valid():
        try:
            job = queue_index(form.cleaned_data["folder"])
        except (ValueError, ValidationError):
            form.add_error(None, _("Die Auswahl überschneidet sich mit einem laufenden oder ungeklärten Auftrag."))
        else:
            messages.info(
                request, _("Indizierung beauftragt. Dies ist keine Freigabe; bitte jede neue Version prüfen.")
            )
            return redirect("job_detail", job_id=job.pk)
    return render(request, "archive/index_start.html", {"form": form}, status=400)


@never_cache
@login_required
@require_GET
def folder_detail(request, folder_id):
    folder = get_object_or_404(m.SourceFolder, pk=folder_id)
    folder.state_label = STATES[folder.index_state]
    record = folder.index_history.select_related("scan__job", "folder").order_by("-created_at").first()
    entries = []
    if record:
        describe(record.scan.job)
        entries = Paginator(record.scan.entries.filter(folder=folder).order_by("relative_path"), 25).get_page(
            request.GET.get("page")
        )
        for entry in entries:
            entry.error_message = (
                ERRORS.get(entry.error_code, _("Dateiverarbeitung fehlgeschlagen.")) if entry.error_code else ""
            )
    return render(
        request,
        "archive/index_folder.html",
        {
            "folder": folder,
            "record": record,
            "entries": entries,
            "marker_verified": json_published(record),
            "worker_available": worker_is_healthy(),
            "pending_count": review_files().filter(source_version__source_file__folder=folder).count(),
            "form": IndexSelection(initial={"folder": folder.relative_path}),
        },
    )


@never_cache
@login_required
@require_GET
def review_queue(request):
    files = review_files().select_related("source_version__source_file").order_by("created_at", "pk")
    if request.GET.get("folder"):
        try:
            identifier = UUID(request.GET["folder"])
        except ValueError:
            from django.http import Http404

            raise Http404 from None
        folder = get_object_or_404(m.SourceFolder, pk=identifier)
        files = files.filter(source_version__source_file__folder=folder)
    page = Paginator(files, 25).get_page(request.GET.get("page"))
    for file in page:
        file.review_label = REVIEW[file.review_state]
        file.candidate_label = CANDIDATES[file.candidate_state]
    query = request.GET.copy()
    query.pop("page", None)
    return render(request, "archive/review_queue.html", {"page": page, "filters": query.urlencode()})
