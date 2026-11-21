"""Future bundles pin the released image and preserve immutable source examples."""

import re
import tarfile
from pathlib import Path

import pytest

from scripts.package_install import FILES, build_bundle

ROOT = Path(__file__).resolve().parent.parent
IMAGE = "ghcr.io/tostman1/notenarchiv@sha256:" + "a" * 64


def test_future_bundle_is_standalone_pinned_and_reproducible(tmp_path):
    first, second = tmp_path / "first.tar.gz", tmp_path / "second.tar.gz"
    before = {name: (ROOT / name).read_bytes() for name in FILES}
    build_bundle(first, IMAGE)
    build_bundle(second, IMAGE)
    assert first.read_bytes() == second.read_bytes()
    with tarfile.open(first) as archive:
        assert set(archive.getnames()) == {*FILES, "release-digest.txt"}
        for name in ("configuration.yaml", "scripts/prepare-install.sh", "scripts/preflight-host.sh"):
            assert archive.extractfile(name).read().count(IMAGE.encode()) == 1
        compose = archive.extractfile("configuration.yaml").read()
        assert b"${" not in compose and b"CHANGE_UID:CHANGE_GID" in compose
        assert archive.extractfile("release-digest.txt").read() == (IMAGE + "\n").encode()
    assert before == {name: (ROOT / name).read_bytes() for name in FILES}
    with pytest.raises(FileExistsError):
        build_bundle(first, IMAGE)


@pytest.mark.parametrize("image", ["latest", "ghcr.io/tostman1/notenarchiv:latest", IMAGE + "\n"])
def test_bundle_refuses_unpinned_or_malformed_image(tmp_path, image):
    with pytest.raises(ValueError):
        build_bundle(tmp_path / "invalid.tar.gz", image)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("problem", ["missing", "different"])
def test_bundle_refuses_configuration_helper_digest_drift_before_creating_output(tmp_path, problem):
    source = tmp_path / "source"
    source.mkdir()
    for name in FILES:
        destination = source / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((ROOT / name).read_bytes())
    helper = source / "scripts/prepare-install.sh"
    helper.write_text(
        re.sub(
            r"ghcr\.io/tostman1/notenarchiv@sha256:[0-9a-f]{64}",
            "invalid" if problem == "missing" else IMAGE,
            helper.read_text(),
        )
    )
    with pytest.raises(ValueError, match="image reference"):
        build_bundle(tmp_path / "invalid.tar.gz", IMAGE, source=source)
    assert not (tmp_path / "invalid.tar.gz").exists()
