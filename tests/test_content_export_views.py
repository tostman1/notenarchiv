import re

import pytest
from django.test import Client
from django.urls import reverse

from apps.archive.content_geometry_services import append_logical_page
from apps.exports.models import GenerationSnapshot
from tests.test_content_export import confirmed
from tests.test_editions import edition_inputs as legacy_inputs

edition_inputs = legacy_inputs


@pytest.mark.django_db
def test_content_export_requires_login_and_csrf(edition_inputs):
    url = reverse("content_generated_export")
    client = Client(enforce_csrf_checks=True)
    assert client.get(url).status_code == 302
    client.force_login(edition_inputs[0])
    assert client.get(url).status_code == 200
    assert client.post(url, {"action": "authorize"}).status_code == 403
    assert GenerationSnapshot.objects.count() == 0


@pytest.mark.django_db
def test_content_export_explicit_authorization_and_stale_rejection(client, edition_inputs):
    identity, logical_identity, logical, _ = confirmed(edition_inputs)
    client.force_login(edition_inputs[0])
    url = reverse("content_generated_export")
    data = {"editions": [str(identity.pk)], "variant": "READING", "action": "inspect"}
    response = client.post(url, data)
    assert response.status_code == 200
    assert GenerationSnapshot.objects.count() == 0
    token = re.search(r'name="token" value="([^"]+)"', response.content.decode())[1]
    data.update(action="authorize", token=token)
    assert client.post(url, data).status_code == 302
    assert GenerationSnapshot.objects.count() == 1
    assert client.post(url, data).status_code == 302
    assert GenerationSnapshot.objects.count() == 1
    append_logical_page(logical_identity.pk, expected_number=1, source_page_id=logical.source_page_id, orientation=90)
    assert client.post(url, data).status_code == 409
    assert GenerationSnapshot.objects.count() == 1
