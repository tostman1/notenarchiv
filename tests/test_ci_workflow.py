"""CI event policy and stable required check contract."""

import re
from pathlib import Path

from scripts.ci_changes import docs_only


def test_actions_use_reviewed_node24_pins_and_zip_recovery():
    expected = {
        "actions/checkout": "3d3c42e5aac5ba805825da76410c181273ba90b1",
        "actions/cache": "55cc8345863c7cc4c66a329aec7e433d2d1c52a9",
        "astral-sh/setup-uv": "1db35dd8eee11c5894872e0b383ae6c406cf738d",
        "docker/setup-buildx-action": "f87e5991a6d7451dcb8d9637bfbc97413f497069",
        "docker/login-action": "8aa5831fb8d48d8f76594c7ddde61ae58019f550",
        "actions/upload-artifact": "cf430e030ddbb5b0abf93d22962f4752f3646cd9",
        "actions/download-artifact": "9000827ccba6bdab643e8b6fd33ac0654aef8333",
        "actions/attest": "1e69f48acb82d1966a394da916b4c1698aa569d6",
    }
    seen = set()
    for path in Path(".github/workflows").glob("*.yml"):
        text = path.read_text()
        assert "ACTIONS_ALLOW_USE_UNSECURE_NODE_VERSION" not in text
        for action, revision in re.findall(r"uses: ([\w/-]+)@([^\s]+)", text):
            assert revision == expected[action]
            seen.add(action)
        assert text.count("archive: true") == text.count("uses: actions/upload-artifact@")
    assert seen == set(expected)


def test_ci_preserves_names_parallel_jobs_and_release_full_scope():
    workflow = Path(".github/workflows/ci.yml").read_text()
    assert "name: Foundation (ruff + pytest)" in workflow
    assert "name: Container (amd64 + security + synthetic smoke)" in workflow
    assert "needs: foundation" not in workflow
    assert "needs: changes" in workflow
    assert "cancel-in-progress: ${{ github.event_name == 'pull_request' }}" in workflow
    assert "else\n            echo 'docs-only=false'" in workflow
    for action in (
        "uv run pytest",
        "uv run pytest browser/",
        "pip-audit",
        "publication_smoke",
        "container_smoke",
        "sha256sum --check",
    ):
        assert action in workflow


def test_all_runtime_and_security_paths_receive_full_checks():
    for path in (
        "AGENTS.md",
        "REQUIREMENTS.md",
        "ARCHITECTURE.md",
        "docs/RESTORE.md",
        "docs/DEV_WORKFLOW.md",
        "Dockerfile",
        "uv.lock",
        "compose.yaml",
        "configuration.yaml",
        "static/favicon.svg",
        "templates/base.html",
        "config/env.py",
        "scripts/ci_changes.py",
        "tests/test_auth.py",
    ):
        assert not docs_only([path])
        assert not docs_only(["docs/PROGRESS.md", path])
