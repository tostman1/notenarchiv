"""Authenticated business job status and POST-only cooperative cancellation."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST

from apps.jobs.forms import JobFilters
from apps.jobs.models import Job
from apps.jobs.presentation import describe
from apps.jobs.services.lifecycle import request_cancel
from apps.jobs.services.queue import worker_is_healthy


@never_cache
@login_required
@require_GET
def job_list(request):
    form = JobFilters(request.GET)
    if not form.is_valid():
        return render(request, "jobs/list.html", {"form": form}, status=400)
    jobs = Job.objects.defer("payload").order_by("-created_at", "-id")
    for field, value in form.cleaned_data.items():
        if value:
            jobs = jobs.filter(**{field: value})
    page = Paginator(jobs, 25).get_page(request.GET.get("page"))
    page.object_list = [describe(job) for job in page.object_list]
    query = request.GET.copy()
    query.pop("page", None)
    return render(
        request,
        "jobs/list.html",
        {
            "form": form,
            "page": page,
            "worker_available": worker_is_healthy(),
            "filters": query.urlencode(),
        },
    )


@never_cache
@login_required
@require_GET
def job_detail(request, job_id):
    job = get_object_or_404(Job.objects.defer("payload"), pk=job_id)
    history = list(job.history.order_by("-number")[:20])
    for entry in history:
        describe(entry)
    return render(
        request,
        "jobs/detail.html",
        {
            "job": describe(job),
            "history": history,
            "worker_available": worker_is_healthy(),
        },
    )


@never_cache
@login_required
@require_POST
def job_cancel(request, job_id):
    get_object_or_404(Job, pk=job_id)
    if request_cancel(job_id):
        messages.info(request, _("Der Abbruch wurde angefordert. Laufende Prozesse werden zuerst beendet."))
    else:
        messages.info(request, _("Dieser Auftrag ist bereits beendet."))
    return redirect("job_detail", job_id=job_id)
