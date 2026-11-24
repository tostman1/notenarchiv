"""Source/package boundaries: never publish guessed references or alter RAW."""

import importlib.util
import io
from pathlib import Path

import pytest
from pypdf import PdfReader

from scripts.package_synology_test import CANDIDATE, build, contents


def test_package_requires_digest_and_removes_all_build_inputs(tmp_path):
    with pytest.raises(ValueError):
        contents("ghcr.io/tostman1/notenarchiv:unpublished")
    image = "ghcr.io/tostman1/notenarchiv@sha256:" + "a" * 64
    files = contents(image)
    compose = files["compose.yaml"].decode()
    assert compose.count(image) == 1 and "${" not in compose
    assert "Publication pending" not in compose
    assert "127.0.0.1:8090:8000" in compose and "8089" not in compose
    assert "name: notenarchiv-test" in compose
    assert CANDIDATE in Path("deploy/synology-test/compose.yaml").read_text()
    output = tmp_path / "test.tar.gz"
    build(output, image)
    with pytest.raises(FileExistsError):
        build(output, image)


def test_original_demo_preserves_existing_output(tmp_path):
    spec = importlib.util.spec_from_file_location("demo", Path("deploy/synology-test/demo.py"))
    demo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(demo)
    target = tmp_path / "demo"
    demo.create(target)
    originals = {p.relative_to(target): p.read_bytes() for p in target.rglob("*.pdf")}
    assert len(originals) == 6
    for data in originals.values():
        reader = PdfReader(io.BytesIO(data))
        assert len(reader.pages) in {1, 2}
        assert "SYNTHETIC TEST ONLY" in reader.pages[0].extract_text()
    with pytest.raises(FileExistsError):
        demo.create(target)
    assert originals == {p.relative_to(target): p.read_bytes() for p in target.rglob("*.pdf")}


def test_test_release_keeps_full_stack_before_publication_and_after_pull():
    ci = Path(".github/workflows/ci.yml").read_text()
    release = Path(".github/workflows/release.yml").read_text()
    assert "scripts.synology_stack_smoke --image notenarchiv-ci:verified" in ci
    assert 'scripts.synology_stack_smoke --image "$(cat release-digest.txt)"' in release
    assert "scripts/package_synology_test.py" in release
    assert "docker load -i verified-image.tar" in release
    assert "docker build " not in release and "docker buildx build" not in release
