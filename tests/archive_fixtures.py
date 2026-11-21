"""Synthetic archive inputs shared by database and workflow tests."""

import hashlib

import pytest

from apps.archive import models as m
from apps.archive import services
from tests.pdf_fixtures import A4, pdf

PAGE = {
    "media_box": [0, 0, *A4],
    "crop_box": [0, 0, *A4],
    "user_unit": 1,
    "rotation": 0,
    "width_points": A4[0],
    "height_points": A4[1],
}


@pytest.fixture
def archive(db):
    folder = m.SourceFolder.objects.create(relative_path="Synthetic")
    data = pdf()
    version, created = services.observe_version(
        folder.pk,
        "Synthetic/scan.pdf",
        sha256=hashlib.sha256(data).hexdigest(),
        byte_size=len(data),
        mtime_ns=1000,
        pdf_state="VALID",
        page_info=[PAGE],
    )
    assert created
    file = services.register_base(version.pk, "_Ungeprueft/synthetic.pdf")
    return folder, version, file, data
