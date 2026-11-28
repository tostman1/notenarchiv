"""Explicit display-space splits retain all original history and approval gates."""

import pytest
from django.core.exceptions import ValidationError
from django.test import Client
from django.urls import reverse

from apps.archive import models as m
from apps.archive import region_editor_services as editor
from apps.archive.services import ArchiveConflict
from tests.test_preview import preview  # noqa: F401
from tests.test_region_editor_services import editable, save  # noqa: F401


def split(item, **kwargs):
    values = dict(
        expected_file_revision=item.file.revision,
        source_version_id=item.file.source_version_id,
        selection={"page": 0, "box": [0.1, 0.2, 0.9, 0.8]},
        axis="vertical",
        fraction=0.5,
    )
    values.update(kwargs)
    return editor.split_rectangle(item.file.pk, **values)


@pytest.mark.django_db
@pytest.mark.parametrize("axis", ["horizontal", "vertical"])
def test_split_creates_two_distinct_regions_without_replacing_history(editable, axis):  # noqa: F811
    original = save(editable)
    children = split(editable, axis=axis)
    assert len({original.region_id, *(child.region_id for child in children)}) == 3
    assert all(
        child.number == 1 and child.region.source_page_id == original.region.source_page_id for child in children
    )
    assert m.PageRegionRevision.objects.count() == 3
    assert children[0].bounds_points != children[1].bounds_points
    assert m.ContentInspection.objects.count() == m.ContentConfirmation.objects.count() == 0
    assert m.ContentEditionRevision.objects.count() == m.LogicalPageRevision.objects.count() == 0


@pytest.mark.django_db
@pytest.mark.parametrize("fraction", [True, 0, 1, -1, float("nan"), float("inf"), 10**400])
def test_invalid_split_has_no_writes(editable, fraction):  # noqa: F811
    with pytest.raises(ValidationError):
        split(editable, fraction=fraction)
    assert not m.PageRegion.objects.exists()


@pytest.mark.django_db
def test_split_rolls_back_both_children_on_late_conflict(editable, monkeypatch):  # noqa: F811
    actual = editor._save_verified
    calls = 0

    def fail_second(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise ArchiveConflict()
        return actual(*args, **kwargs)

    monkeypatch.setattr(editor, "_save_verified", fail_second)
    with pytest.raises(ArchiveConflict):
        split(editable)
    assert not m.PageRegion.objects.exists()
    assert not m.PageRegionRevision.objects.exists()


@pytest.mark.django_db
def test_split_action_requires_csrf_and_explicit_acknowledgement(preview, monkeypatch):  # noqa: F811
    from django.contrib.auth import get_user_model

    file, _data, _target = preview
    user = get_user_model().objects.create_user(username="split-reviewer", password="synthetic-password")
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)
    url = reverse("archive_review_detail", args=[file.pk])
    payload = {
        "action": "region_split",
        "page": 1,
        "left": 0,
        "top": 0,
        "right": 100,
        "bottom": 100,
        "expected_file_revision": file.revision,
        "source_version_id": str(file.source_version_id),
        "expected_region_number": 0,
        "split_axis": "horizontal",
        "split_percent": 50,
    }
    calls = []
    monkeypatch.setattr(editor, "split_rectangle", lambda *args, **kwargs: calls.append(kwargs))
    assert client.post(url, payload).status_code == 403
    assert client.get(url).status_code == 200
    from apps.archive.review_forms import RegionSplitForm

    rendered = RegionSplitForm().as_p()
    assert "required" not in rendered
    assert not RegionSplitForm({"split_axis": "vertical", "split_percent": 50}).is_valid()
    from django.conf import settings

    payload["csrfmiddlewaretoken"] = client.cookies[settings.CSRF_COOKIE_NAME].value
    assert client.post(url, payload).status_code == 302
    assert calls == []
    payload["split_acknowledged"] = "on"
    assert client.post(url, payload).status_code == 302
    assert len(calls) == 1
    assert calls[0]["axis"] == "horizontal" and calls[0]["fraction"] == 0.5
    assert calls[0]["selection"] == {"page": 0, "box": [0, 0, 1, 1]}
    assert m.ContentInspection.objects.count() == m.ContentConfirmation.objects.count() == 0
