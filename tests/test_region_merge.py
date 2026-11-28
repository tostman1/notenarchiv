"""Conservative same-page merges preserve history and reject implicit added areas."""

import pytest
from django.core.exceptions import ValidationError

from apps.archive import models as m
from apps.archive import region_editor_services as editor
from apps.archive.content_geometry_services import append_region
from apps.archive.services import ArchiveConflict
from tests.test_preview import preview  # noqa: F401
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


@pytest.mark.django_db
def test_merge_action_is_separate_csrf_protected_and_requires_acknowledgement(preview, monkeypatch):  # noqa: F811
    from uuid import uuid4

    from django.conf import settings
    from django.contrib.auth import get_user_model
    from django.test import Client
    from django.urls import reverse

    file, _data, _target = preview
    actor = get_user_model().objects.create_user(username="merge-reviewer")
    client = Client(enforce_csrf_checks=True)
    url = reverse("archive_review_detail", args=[file.pk])
    payload = {
        "action": "region_merge",
        "expected_file_revision": file.revision,
        "source_version_id": str(file.source_version_id),
        "first_region": str(uuid4()),
        "second_region": str(uuid4()),
    }
    assert Client().post(url, payload).status_code == 302
    client.force_login(actor)
    assert client.post(url, payload).status_code == 403
    assert client.get(url).status_code == 200
    payload["csrfmiddlewaretoken"] = client.cookies[settings.CSRF_COOKIE_NAME].value
    calls = []
    monkeypatch.setattr(editor, "merge_adjacent_regions", lambda *args, **kwargs: calls.append(kwargs))
    assert client.post(url, payload).status_code == 302
    assert calls == []
    payload["merge_acknowledged"] = "on"
    assert client.post(url, payload).status_code == 302
    assert len(calls) == 1 and len(calls[0]["region_revision_ids"]) == 2
    assert not m.ContentInspection.objects.exists() and not m.ContentConfirmation.objects.exists()


@pytest.mark.django_db
def test_merge_controls_have_independent_form_and_revision_pins(editable):  # noqa: F811
    from django.contrib.auth import get_user_model
    from django.test import Client
    from django.urls import reverse

    split(editable)
    client = Client()
    client.force_login(get_user_model().objects.create_user(username="merge-form-reviewer"))
    response = client.get(reverse("archive_review_detail", args=[editable.file.pk]))
    html = response.content.decode()
    assert '<form method="post" id="region-merge">' in html
    assert 'name="first_region" required' in html and 'name="second_region" required' in html
    assert 'id="merge_merge_acknowledged"' in html
