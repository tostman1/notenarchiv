"""Catalog correction UI is explicit, CSRF-protected and history-retaining."""

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from apps.catalog.collection_services import add_membership
from apps.catalog.models import AssociationWithdrawal, Collection, CollectionMembership, Work


@pytest.mark.django_db
def test_catalog_correction_ui_fences_replacement_and_retains_history():
    actor = get_user_model().objects.create_user(username="synthetic-correction-ui")
    first, second = Work.objects.create(title="First"), Work.objects.create(title="Second")
    old = add_membership(Collection.objects.create(title="Synthetic").pk, first.pk, position=0)
    url = reverse("catalog_correction", kwargs={"kind": "membership", "identifier": old.pk})
    client = Client()
    assert client.get(url).status_code == 302
    secure = Client(enforce_csrf_checks=True)
    secure.force_login(actor)
    assert secure.post(url, {}).status_code == 403
    client.force_login(actor)
    assert client.get(url).status_code == 200
    detail = client.get(reverse("catalog_detail", kwargs={"entity": "works", "record_id": first.pk}))
    assert url.encode() in detail.content
    assert not AssociationWithdrawal.objects.exists()
    values = {"revision": old.revision, "action": "replace", "reason": "Wrong work", "work": second.pk, "position": 0}
    replacement_response = client.post(url, values)
    assert replacement_response.status_code == 302
    replacement_page = client.get(replacement_response.url)
    assert b'<label for="id_action">Aktion:</label>' in replacement_page.content
    assert b'value="withdraw"' in replacement_page.content
    assert client.post(url, values).status_code == 409
    assert client.get(url).status_code == 200
    assert AssociationWithdrawal.objects.count() == 1
    assert CollectionMembership.objects.count() == 2
    old.refresh_from_db()
    assert old.work_id == first.pk
    assert client.post(url, {"action": "unknown"}).status_code == 400
