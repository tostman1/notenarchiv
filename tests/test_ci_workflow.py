"""CI event policy and stable required check contract."""

from pathlib import Path

from scripts.ci_changes import docs_only


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
