"""Compound naming stays neutral and delegates to the existing copy primitive."""

import pytest
from django.core.exceptions import ValidationError

from apps.archive import publication
from tests.test_content_geometry_models import page

pytestmark = pytest.mark.django_db


def test_compound_naming_and_title_validation(monkeypatch):
    source_page = page()
    calls = []
    monkeypatch.setattr(publication, "queue_copy", lambda identifier, **kwargs: calls.append((identifier, kwargs)))
    for title in (None, "", " ", "x" * 201):
        with pytest.raises(ValidationError):
            publication.queue_compound_copy(source_page.source_version_id, title=title)
    assert not calls
    publication.queue_compound_copy(source_page.source_version_id, title="Testsammlung / Band 1")
    identifier, options = calls[0]
    assert identifier == source_page.source_version_id
    assert options["_preferred_path"].startswith("Sammlungen/Testsammlung")
    assert options["_preferred_path"].endswith(".pdf")
    assert "_Ungeprueft" not in options["_preferred_path"]
    assert source_page.source_version.source_file.document.pk
