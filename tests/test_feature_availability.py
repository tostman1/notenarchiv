"""Integrated capabilities must not inherit obsolete web-shell preview claims."""

import pytest

from config.features import FEATURES


@pytest.mark.django_db
@pytest.mark.parametrize("test_distribution", [False, True])
def test_honest_integrated_availability(client, django_user_model, settings, test_distribution):
    settings.TEST_DISTRIBUTION = test_distribution
    client.force_login(django_user_model.objects.create_user("synthetic-capability-reviewer"))
    body = client.get("/").content.decode()
    assert ("Testversion – ausschließlich für Testdaten" in body) is test_distribution
    assert "Archivimport, Projekte und Ausgabe folgen" not in body
    assert "Teilnehmerauswahl und Generierung folgen" not in body
    for key, _label, state, _package, _route in FEATURES:
        marker = f'data-feature="{key}" data-availability="{state}"'
        assert marker in body
        item = body.split(marker, 1)[1].split("</li>", 1)[0]
        if state == "AVAILABLE":
            assert "href=" in item and "disabled" not in item
        else:
            assert 'disabled aria-disabled="true"' in item
            assert "href=" not in item and "Noch nicht verfügbar" in item


def test_inventory_routes_match_integrated_operations():
    from django.urls import reverse

    for _key, _label, state, _package, route in FEATURES:
        assert (route is not None) is (state == "AVAILABLE")
        if route:
            assert reverse(route).startswith("/")
