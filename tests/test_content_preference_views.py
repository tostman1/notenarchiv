import pytest
from django.test import Client
from django.urls import reverse

from apps.archive.content_geometry_services import append_logical_page
from apps.archive.models import EditionPreferenceChange, PreferredEdition
from tests.test_content_export import confirmed
from tests.test_editions import edition_inputs as legacy_inputs

edition_inputs = legacy_inputs


@pytest.mark.django_db
def test_preference_view_requires_login_csrf_and_explicit_action(edition_inputs):
    identity, _, _, _ = confirmed(edition_inputs)
    url = reverse("content_preference", args=[identity.pk])
    client = Client(enforce_csrf_checks=True)
    assert client.get(url).status_code == 302
    client.force_login(edition_inputs[0])
    assert client.get(url).status_code == 200
    assert client.post(url, {"action": "set", "revision": 0}).status_code == 403
    assert not PreferredEdition.objects.exists()
    assert not EditionPreferenceChange.objects.exists()


@pytest.mark.django_db
def test_preference_view_set_stale_clear_and_changed_content(client, edition_inputs):
    identity, logical_identity, logical, _ = confirmed(edition_inputs)
    client.force_login(edition_inputs[0])
    url = reverse("content_preference", args=[identity.pk])
    identity.arrangement.refresh_from_db()
    revision = identity.arrangement.revision
    data = {"action": "set", "revision": revision}
    assert client.post(url, data).status_code == 302
    preference = PreferredEdition.objects.get()
    assert preference.content_edition_id == identity.pk
    assert client.post(url, data).status_code == 409
    assert EditionPreferenceChange.objects.count() == 1
    assert client.post(url, {"action": "clear", "revision": revision + 1}).status_code == 302
    preference.refresh_from_db()
    assert preference.content_edition_id is None and preference.assignment_id is None
    append_logical_page(logical_identity.pk, expected_number=1, source_page_id=logical.source_page_id, orientation=90)
    assert client.post(url, {"action": "set", "revision": revision + 2}).status_code == 409
    assert EditionPreferenceChange.objects.count() == 2
    assert client.post(url, {"action": "unknown", "revision": revision + 2}).status_code == 400
