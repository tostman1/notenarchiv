"""Explicit display-space splits retain all original history and approval gates."""

import pytest
from django.core.exceptions import ValidationError

from apps.archive import models as m
from apps.archive import region_editor_services as editor
from apps.archive.services import ArchiveConflict
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
