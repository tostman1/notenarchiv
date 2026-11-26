"""Thin authenticated management views over explicit catalog service APIs."""

from functools import reduce
from operator import or_
from uuid import UUID

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.catalog.forms import DeleteForm, SearchForm, TemplateApplyForm
from apps.catalog.models import Arrangement, InstrumentationTemplate, InstrumentVariant, Work, normalized
from apps.catalog.registry import SCREENS
from apps.catalog.services import apply_template, delete_record, save_record


def screen_for(entity):
    if entity not in SCREENS:
        raise Http404
    return SCREENS[entity]


def cells(record, screen):
    values = []
    for field, _label in screen.columns:
        value = getattr(record, field)
        if callable(value):
            value = value()
        if field == "active":
            value = _("Aktiv") if value else _("Inaktiv")
        elif field == "expectations_defined":
            value = _("Festgelegt") if value else _("Unbekannt")
        elif isinstance(value, bool):
            value = _("Ja") if value else _("Nein")
        values.append(value if value not in (None, "") else "—")
    return values


def add_errors(form, error):
    if hasattr(error, "message_dict"):
        for field, errors in error.message_dict.items():
            if field in form.fields:
                form.add_error(field, errors)
            else:
                form.add_error(None, errors if field == "__all__" else _("Prüfen Sie Bezeichnung und Referenzen."))
    else:
        form.add_error(None, error)


def context(entity, **values):
    return {"entity": entity, "screen": screen_for(entity), "screens": SCREENS, **values}


@never_cache
@login_required
@require_GET
def record_list(request, entity):
    screen = screen_for(entity)
    params = request.GET.copy()
    params.setdefault("active", "1")
    form = SearchForm(params)
    if not hasattr(screen.model, "active"):
        form.fields.pop("active")
        params.pop("active", None)
    if not form.is_valid():
        return render(request, "catalog/list.html", context(entity, form=form), status=400)
    query = screen.model.objects.select_related(*screen.related).order_by(screen.search[0], "pk")
    for parent in ("arrangement", "template", "work", "instrument"):
        if hasattr(screen.model, parent) and request.GET.get(parent):
            try:
                query = query.filter(**{parent + "_id": UUID(request.GET[parent])})
            except ValueError:
                form.add_error(None, _("Ungültiger Bezug. Bitte öffnen Sie die Liste erneut."))
                return render(request, "catalog/list.html", context(entity, form=form), status=400)
    if hasattr(screen.model, "active") and form.cleaned_data["active"] in {"1", "0"}:
        query = query.filter(active=form.cleaned_data["active"] == "1")
    if form.cleaned_data["q"]:
        value = normalized(form.cleaned_data["q"])
        query = query.filter(reduce(or_, (Q(**{field + "__contains": value}) for field in screen.search))).distinct()
    page = Paginator(query, 25).get_page(request.GET.get("page"))
    rows = [(record, cells(record, screen)) for record in page.object_list]
    params.pop("page", None)
    return render(
        request, "catalog/list.html", context(entity, form=form, page=page, rows=rows, filters=params.urlencode())
    )


@never_cache
@login_required
@require_GET
def record_detail(request, entity, record_id):
    screen = screen_for(entity)
    record = get_object_or_404(screen.model.objects.select_related(*screen.related), pk=record_id)
    extra = {}
    if isinstance(record, Work):
        extra["collection_memberships"] = record.collection_memberships.select_related("collection").order_by(
            "position", "pk"
        )[:200]
        extra["component_relationships"] = record.component_relationships.select_related("component").order_by(
            "position", "pk"
        )[:200]
        extra["alternative_titles"] = record.alternative_titles.order_by("title_key", "pk")[:200]
        extra["arrangements"] = record.arrangements.select_related("work").order_by(
            "arranger_key", "edition_key", "pk"
        )[:200]
    if isinstance(record, InstrumentVariant):
        extra["parts"] = record.parts.select_related("instrument").order_by("code_key", "pk")[:200]
    if isinstance(record, Arrangement):
        extra["expectations"] = record.expected_parts.select_related("part__instrument").order_by("pk")[:200]
        extra["apply_form"] = TemplateApplyForm(initial={"expected_revision": record.revision})
    if isinstance(record, InstrumentationTemplate):
        extra["entries"] = record.entries.select_related("part__instrument").order_by("pk")[:200]
    return render(
        request,
        "catalog/detail.html",
        context(
            entity,
            record=record,
            fields=zip((label for _field, label in screen.columns), cells(record, screen), strict=True),
            **extra,
        ),
    )


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def record_edit(request, entity, record_id=None):
    screen = screen_for(entity)
    record = get_object_or_404(screen.model, pk=record_id) if record_id else None
    initial = {
        field: request.GET[field] for field in ("work", "instrument", "arrangement", "template") if field in request.GET
    }
    form = screen.form(request.POST if request.method == "POST" else None, instance=record, initial=initial)
    if request.method == "POST" and form.is_valid():
        try:
            saved = save_record(form.save(commit=False), expected_revision=form.cleaned_data["expected_revision"])
        except ValidationError as error:
            add_errors(form, error)
        else:
            messages.success(request, _("Der Datensatz wurde gespeichert."))
            return redirect("catalog_detail", entity=entity, record_id=saved.pk)
    return render(request, "catalog/form.html", context(entity, form=form, record=record))


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def record_delete(request, entity, record_id):
    screen = screen_for(entity)
    record = get_object_or_404(screen.model, pk=record_id)
    form = DeleteForm(
        request.POST if request.method == "POST" else None, initial={"expected_revision": record.revision}
    )
    if request.method == "POST" and form.is_valid():
        try:
            delete_record(record, expected_revision=form.cleaned_data["expected_revision"])
        except ValidationError as error:
            add_errors(form, error)
        else:
            messages.success(request, _("Der unbenutzte Datensatz wurde gelöscht."))
            return redirect("catalog_list", entity=entity)
    return render(request, "catalog/delete.html", context(entity, form=form, record=record))


@never_cache
@login_required
@require_POST
def template_apply(request, record_id):
    arrangement = get_object_or_404(Arrangement, pk=record_id)
    form = TemplateApplyForm(request.POST)
    if form.is_valid():
        try:
            apply_template(
                arrangement.pk,
                form.cleaned_data["template"],
                expected_revision=form.cleaned_data["expected_revision"],
                replace=form.cleaned_data["replace"],
            )
        except ValidationError as error:
            add_errors(form, error)
        else:
            messages.success(request, _("Die Besetzung wurde als unabhängige Erwartungsliste übernommen."))
            return redirect("catalog_detail", entity="arrangements", record_id=arrangement.pk)
    return render(request, "catalog/apply.html", context("arrangements", record=arrangement, form=form), status=400)
