"""CRUD screens, controlled references, CSRF, search and template workflow."""

from uuid import uuid4

import pytest
from django.test import Client
from django.urls import reverse

from apps.catalog import models, services
from apps.catalog.registry import SCREENS
from apps.members.models import Member
from tests.test_catalog import catalog as _catalog_fixture
from tests.test_catalog import create

catalog = _catalog_fixture


@pytest.fixture
def manager(db, django_user_model, client):
    client.force_login(django_user_model.objects.create_user("synthetic-catalog"))
    return client


def url(action, entity, record=None):
    args = [entity] + ([record.pk] if record else [])
    return reverse("catalog_" + action, args=args)


def data_for(entity, catalog):
    work, arrangement, instrument, part = catalog
    values = {
        "works": {"title": "Synthetic new work", "composer": "Synthetic composer"},
        "arrangements": {"work": work.pk, "arranger": "Synthetic arranger", "edition": "Synthetic edition"},
        "instruments": {
            "name": "Synthetic other instrument",
            "family": "Synthetic",
            "transposition": "C",
            "clef": "BASS",
        },
        "parts": {"instrument": instrument.pk, "code": "2", "label": "Synthetic second"},
        "work-aliases": {"work": work.pk, "alias": "Synthetic alias"},
        "instrument-aliases": {"part": part.pk, "alias": "Synthetic part alias"},
        "expectations": {"arrangement": arrangement.pk, "part": part.pk, "required": True},
        "templates": {"name": "Synthetic instrumentation"},
        "members": {"name": "Synthetic member", "regular_part": part.pk},
    }
    if entity == "template-parts":
        template = create(models.InstrumentationTemplate, name="Synthetic template")
        values[entity] = {"template": template.pk, "part": part.pk, "required": True}
    return {**values[entity], "active": True, "expected_revision": 0}


@pytest.mark.django_db
@pytest.mark.parametrize("entity", list(SCREENS))
def test_all_management_screens_require_login(client, entity):
    for action in ("list", "create"):
        response = client.get(url(action, entity))
        assert response.status_code == 302 and response.url.startswith("/login/")


@pytest.mark.parametrize("entity", list(SCREENS))
def test_create_read_edit_and_delete_unused_records(manager, catalog, entity):
    assert manager.get(url("create", entity)).status_code == 200
    data = data_for(entity, catalog)
    response = manager.post(url("create", entity), data)
    assert response.status_code == 302, response.content.decode()
    detail = manager.get(response.url)
    assert detail.status_code == 200 and "no-store" in detail["Cache-Control"]
    record = detail.context["record"]
    edited = {**data, "expected_revision": record.revision}
    assert manager.post(url("edit", entity, record), edited).status_code == 302
    record.refresh_from_db()
    assert record.revision == 2
    record_id = record.pk
    assert manager.get(url("delete", entity, record)).status_code == 200
    assert SCREENS[entity].model.objects.filter(pk=record.pk).exists()
    assert manager.post(url("delete", entity, record), {"expected_revision": record.revision}).status_code == 200
    response = manager.post(url("delete", entity, record), {"expected_revision": record.revision, "confirm": True})
    assert response.status_code == 302
    assert not SCREENS[entity].model.objects.filter(pk=record_id).exists()


def test_search_equal_names_and_unicode_are_preserved(manager, catalog):
    work, _arrangement, _instrument, part = catalog
    for _index in range(2):
        create(Member, name="Synthetische Straße", membership_id="gleich", regular_part=part)
        create(models.Work, title="Synthetische Straße")
    for entity in ("members", "works"):
        response = manager.get(url("list", entity), {"q": "STRASSE"})
        assert response.status_code == 200 and len(response.context["rows"]) == 2
    create(models.WorkAlias, work=work, alias="Synthetisches Suchkürzel")
    response = manager.get(url("list", "works"), {"q": "SUCHKÜRZEL"})
    assert len(response.context["rows"]) == 1 and response.context["rows"][0][0].pk == work.pk
    assert manager.get(url("list", "works"), {"active": "invalid"}).status_code == 400
    assert manager.get(url("list", "unknown-model")).status_code == 404
    assert manager.get(reverse("catalog_detail", args=["works", uuid4()])).status_code == 404


def test_csrf_protected_mutations_and_protected_deletion(manager, catalog, django_user_model):
    work, _arrangement, _instrument, part = catalog
    strict = Client(enforce_csrf_checks=True)
    strict.force_login(django_user_model.objects.get(username="synthetic-catalog"))
    data = data_for("members", catalog)
    assert strict.post(url("create", "members"), data).status_code == 403
    strict.get(url("create", "members"))
    data["csrfmiddlewaretoken"] = strict.cookies["notenarchiv_csrftoken"].value
    assert strict.post(url("create", "members"), data).status_code == 302
    assert Member.objects.get().regular_part == part
    protected = manager.post(url("delete", "works", work), {"expected_revision": work.revision, "confirm": True})
    assert protected.status_code == 200 and "Deaktivieren" in protected.content.decode()
    assert models.Work.objects.filter(pk=work.pk).exists()
    bad = manager.post(
        url("create", "members"),
        {"name": "Invalid", "regular_part": "free text", "active": True, "expected_revision": 0},
    )
    assert bad.status_code == 200 and Member.objects.count() == 1


def test_template_workflow_checks_revision_confirmation_and_copy(manager, catalog):
    _work, arrangement, _instrument, part = catalog
    template = create(models.InstrumentationTemplate, name="Synthetic template")
    entry = create(models.TemplatePart, template=template, part=part)
    detail = manager.get(url("detail", "arrangements", arrangement))
    assert "Unbekannt" in detail.content.decode()
    apply_url = reverse("catalog_apply_template", args=[arrangement.pk])
    assert manager.get(apply_url).status_code == 405
    payload = {"template": template.pk, "expected_revision": arrangement.revision}
    assert manager.post(apply_url, payload).status_code == 302
    arrangement.refresh_from_db()
    assert arrangement.expectations_defined and arrangement.expected_parts.get().required
    entry.required = False
    services.save_record(entry, expected_revision=entry.revision)
    assert arrangement.expected_parts.get().required
    assert manager.post(apply_url, {**payload, "expected_revision": arrangement.revision}).status_code == 400
    response = manager.post(
        apply_url, {"template": template.pk, "expected_revision": arrangement.revision, "replace": True}
    )
    assert response.status_code == 302 and not arrangement.expected_parts.get().required
    page = manager.get(url("list", "expectations"), {"arrangement": str(arrangement.pk)})
    assert len(page.context["rows"]) == 1
    assert manager.get(url("list", "expectations"), {"arrangement": "invalid"}).status_code == 400


def test_pagination_escaping_and_stale_form_errors(manager, catalog):
    work, _arrangement, _instrument, _part = catalog
    unsafe = create(models.Work, title="<script>synthetic</script>")
    body = manager.get(url("detail", "works", unsafe)).content.decode()
    assert "&lt;script&gt;" in body and "<script>synthetic" not in body
    for index in range(26):
        create(models.Work, title=f"Synthetic page {index}")
    page = manager.get(url("list", "works"))
    assert len(page.context["rows"]) == 25
    updated = manager.post(
        url("edit", "works", work),
        {"title": work.title, "composer": "Synthetic fresh", "active": True, "expected_revision": work.revision},
    )
    assert updated.status_code == 302
    stale = manager.post(
        url("edit", "works", work),
        {"title": work.title, "composer": "Synthetic stale", "active": True, "expected_revision": work.revision},
    )
    assert stale.status_code == 200 and "inzwischen geändert" in stale.content.decode()
    assert models.Work.objects.get(pk=work.pk).composer == "Synthetic fresh"
