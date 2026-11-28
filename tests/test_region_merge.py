"""Conservative same-page merges preserve history and reject implicit added areas."""

import pytest
from django.core.exceptions import ValidationError

from apps.archive import models as m
from apps.archive import region_editor_services as editor
from apps.archive.content_geometry_services import append_region
from apps.archive.services import ArchiveConflict
from tests.test_region_editor_services import editable, save  # noqa: F401
from tests.test_region_split import split


def merge(item, revisions, **changes):
    arguments = dict(
        expected_file_revision=item.file.revision,
        source_version_id=item.file.source_version_id,
        region_revision_ids=[revision.pk for revision in revisions],
    )
    arguments.update(changes)
    return editor.merge_adjacent_regions(item.file.pk, **arguments)


@pytest.mark.django_db
@pytest.mark.parametrize("axis", ["horizontal", "vertical"])
def test_merge_split_children_creates_new_identity_retaining_history(editable, axis):  # noqa: F811
    children = split(editable, axis=axis)
    result = merge(editable, children)
    assert result.region_id not in {child.region_id for child in children}
    assert result.bounds_points == [
        min(child.bounds_points[0] for child in children),
        min(child.bounds_points[1] for child in children),
        max(child.bounds_points[2] for child in children),
        max(child.bounds_points[3] for child in children),
    ]
    assert m.PageRegionRevision.objects.count() == 3
    assert not m.ContentInspection.objects.exists() and not m.ContentConfirmation.objects.exists()


@pytest.mark.django_db
def test_merge_rejects_historical_or_duplicate_regions_without_writes(editable):  # noqa: F811
    children = split(editable)
    append_region(children[0].region_id, expected_number=1, bounds_points=children[0].bounds_points)
    with pytest.raises(ArchiveConflict):
        merge(editable, children)
    with pytest.raises(ValidationError):
        merge(editable, [children[1], children[1]])
    assert m.PageRegion.objects.count() == 2


@pytest.mark.django_db
def test_merge_rejects_gaps_and_overlap_without_adding_music(editable):  # noqa: F811
    first = save(editable, selection={"page": 0, "box": [0, 0, 0.4, 1]})
    second = save(editable, selection={"page": 0, "box": [0.6, 0, 1, 1]})
    with pytest.raises(ValidationError, match="adjacent"):
        merge(editable, [first, second])
    overlap = save(editable, selection={"page": 0, "box": [0.2, 0, 1, 1]})
    with pytest.raises(ValidationError, match="adjacent"):
        merge(editable, [first, overlap])
    assert m.PageRegion.objects.count() == 3


@pytest.mark.django_db
@pytest.mark.parametrize("identifier", [b"not-a-uuid", 1, None, {}, "invalid"])
def test_merge_rejects_malformed_uuid_types(editable, identifier):  # noqa: F811
    children = split(editable)
    with pytest.raises(ValidationError, match="UUID"):
        merge(editable, children, region_revision_ids=[children[0].pk, identifier])
    assert m.PageRegion.objects.count() == 2


@pytest.mark.django_db
@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
def test_merge_preserves_exact_decimal_union_with_offset_crop_and_user_unit(editable, rotation, monkeypatch):  # noqa: F811
    from apps.archive import services
    from tests.test_archive_workflow import receipt

    folder = m.SourceFolder.objects.create(relative_path="Transformed merge")
    version, _ = services.observe_version(
        folder.pk, "Transformed merge/music.pdf", sha256="b" * 64, byte_size=100, pdf_state="UNCHECKED"
    )
    services.record_validation(
        version.pk,
        expected_revision=version.revision,
        pdf_state="VALID",
        page_info=[
            {
                "media_box": [0, 0, 500, 700],
                "crop_box": [10, 20, 480, 680],
                "rotation": rotation,
                "user_unit": 1.3,
                "width_points": 611,
                "height_points": 858,
            }
        ],
        original_crop_boxes=[[10, 20, 480, 680]],
    )
    editable.file, _operation = receipt(services.register_base(version.pk, "transformed-merge.pdf"))
    monkeypatch.setattr(editor, "preview_file", lambda *args, **kwargs: editable.file)
    page = version.pages.get()
    children = []
    for bounds in ([20.1, 40.2, 200.3, 407.7], [200.3, 40.2, 500.4, 407.7]):
        identity = m.PageRegion.objects.create(source_page=page)
        children.append(append_region(identity.pk, expected_number=0, bounds_points=bounds))
    result = merge(editable, children)
    assert result.bounds_points == [20.1, 40.2, 500.4, 407.7]


@pytest.mark.django_db
def test_merge_rechecks_health_and_file_pin_before_creating_identity(editable, monkeypatch):  # noqa: F811
    children = split(editable)
    with pytest.raises(ArchiveConflict):
        merge(editable, children, expected_file_revision=editable.file.revision + 1)
    monkeypatch.setattr(
        editor,
        "preview_bytes",
        lambda file: m.ArchiveFile.objects.filter(pk=file.pk).update(publication_state="MISSING"),
    )
    with pytest.raises(ValidationError, match="unavailable"):
        merge(editable, children)
    assert m.PageRegion.objects.count() == 2
