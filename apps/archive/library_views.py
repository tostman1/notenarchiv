"""Read-only German library; catalog expectation editing reuses existing CRUD."""

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, render
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from apps.archive import library_services as service
from apps.archive import models as m
from apps.archive.library_forms import LibraryFilters
from apps.catalog.forms import TemplateApplyForm


@never_cache
@login_required
@require_GET
def library(request):
    form = LibraryFilters(request.GET)
    if not form.is_valid():
        return render(request, "archive/library.html", {"form": form}, status=400)
    page = Paginator(service.search(form.cleaned_data), 25).get_page(request.GET.get("page"))
    for arrangement in page:
        arrangement.completeness_label = service.LABELS[service.completeness(arrangement)]
    query = request.GET.copy()
    query.pop("page", None)
    return render(
        request,
        "archive/library.html",
        {
            "form": form,
            "page": page,
            "filters": query.urlencode(),
            "unresolved": service.pending_files()
            .filter(current_proposal__arrangement__isnull=True, arrangement__isnull=True)
            .count(),
        },
    )


@never_cache
@login_required
@require_GET
def arrangement_detail(request, arrangement_id):
    arrangement = get_object_or_404(service.search({}), pk=arrangement_id)
    rows = Paginator(service.part_rows(arrangement), 25).get_page(request.GET.get("page"))
    editions = Paginator(
        m.ArchiveFile.objects.usable()
        .filter(arrangement=arrangement, pk__in=m.ArchiveAssignment.objects.usable().values("archive_file_id"))
        .select_related("source_version__source_file")
        .prefetch_related(
            Prefetch(
                "assignments",
                queryset=m.ArchiveAssignment.objects.usable().select_related("part__instrument"),
                to_attr="usable_assignments",
            )
        )
        .order_by("pk"),
        10,
    ).get_page(request.GET.get("editions"))
    for file in editions:
        file.physically_verified = service.verify_file(file)
        file.material_label = (
            _("Bestätigt und hash-geprüft")
            if file.physically_verified
            else _("Kopie fehlt oder Hash stimmt nicht; nicht nutzbar")
        )
    return render(
        request,
        "archive/library_arrangement.html",
        {
            "arrangement": arrangement,
            "rows": rows,
            "editions": editions,
            "completeness_label": service.LABELS[service.completeness(arrangement)],
            "pending_count": service.pending_files().filter(current_proposal__arrangement=arrangement).count(),
            "apply_form": TemplateApplyForm(initial={"expected_revision": arrangement.revision}),
            "aliases": arrangement.work.aliases.filter(active=True).order_by("alias_key")[:100],
        },
    )
